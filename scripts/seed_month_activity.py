#!/usr/bin/env python3
"""
Sinh ~1 THÁNG hoạt động giả lập cho cửa hàng test (tenant 'tap-hoa-my-linh').

Bổ sung (additive) lên trên data đã có từ seed_sqlite.py:
  • Nhập hàng (goods_receipts) định kỳ → cập nhật tồn + giá vốn bình quân + price_history
  • Hàng trăm hóa đơn bán hàng theo từng ngày (cuối tuần đông hơn), kèm:
      - invoice_items (snapshot giá), payments, stock_movements (SALE), cập nhật tồn
      - sổ quỹ phiếu thu (cash_transactions IN / SALE), phiếu chi tiền thối (CHANGE)
      - cập nhật thống kê khách hàng (total_spent / total_orders / last_order_at)
      - một phần hóa đơn bán NỢ (paid < total) → tạo công nợ khách
  • Vài phiếu trả hàng (return_orders) → kardex RETURN + sổ quỹ REFUND
  • Chi phí vận hành thủ công (điện/nước, lương) trong sổ quỹ

Mốc thời gian: 30 ngày gần nhất tính theo ngày kinh doanh VN.

Chạy:  .venv\\Scripts\\python.exe scripts/seed_month_activity.py
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.shared.text import vi_unaccent
from backend.shared.models import Base
from backend.shared.code_generator import CodeSequence

from backend.modules.tenant.models import Tenant
from backend.modules.auth.models import User
from backend.modules.product.models import Product
from backend.modules.customer.models import Customer
from backend.modules.inventory.models import (
    GoodsReceipt, GoodsReceiptItem, Inventory, StockMovement,
)
from backend.modules.sales.models import (
    Invoice, InvoiceItem, Payment, ReturnOrder, ReturnOrderItem,
)
from backend.modules.cashbook.models import CashTransaction
from backend.modules.system.models import PriceHistory

random.seed(2026)
UTC = timezone.utc
VN_TZ = timezone(timedelta(hours=7))
TENANT_SLUG = "tap-hoa-my-linh"
N_DAYS = 30

DB_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'dev.db'}")

CENT = Decimal("0.01")
QTY3 = Decimal("0.001")


def D(v) -> Decimal:
    return Decimal(str(v))


def money(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


def q3(v: Decimal) -> Decimal:
    return Decimal(v).quantize(QTY3, rounding=ROUND_HALF_UP)


class CodeGen:
    """Sinh mã backdate {prefix}{YYYYMMDD}-{NNN} + lưu CodeSequence."""

    def __init__(self) -> None:
        self.counters: dict[tuple[str, str], int] = {}

    def next(self, prefix: str, day: datetime) -> str:
        date_part = day.astimezone(VN_TZ).strftime("%Y%m%d")
        key = (prefix, date_part)
        n = self.counters.get(key, 0) + 1
        self.counters[key] = n
        return f"{prefix}{date_part}-{n:03d}"

    def seed_from_codes(self, codes) -> None:
        """Nạp bộ đếm từ mã đã tồn tại ({PREFIX}{YYYYMMDD}-{NNN}) để không trùng."""
        for code in codes:
            if not code or "-" not in code:
                continue
            head, _, tail = code.rpartition("-")
            if not tail.isdigit() or len(head) < 9 or not head[-8:].isdigit():
                continue
            prefix, date_part = head[:-8], head[-8:]
            key = (prefix, date_part)
            self.counters[key] = max(self.counters.get(key, 0), int(tail))


def at(day_date, hour: int, minute: int) -> datetime:
    """Ghép ngày kinh doanh VN + giờ → datetime UTC."""
    dt_vn = datetime(day_date.year, day_date.month, day_date.day, hour, minute, tzinfo=VN_TZ)
    return dt_vn.astimezone(UTC)


async def main() -> None:
    engine = create_async_engine(DB_URL)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_funcs(dbapi_conn, _):
        try:
            dbapi_conn.create_function("immutable_unaccent", 1, vi_unaccent)
        except Exception:
            pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        tenant = (await db.execute(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )).scalar_one_or_none()
        if tenant is None:
            print(f"❌ Chưa có tenant '{TENANT_SLUG}'. Chạy seed_sqlite.py trước.")
            return
        tid = tenant.id

        users = (await db.execute(
            select(User).where(User.tenant_id == tid)
        )).scalars().all()
        owner = next((u for u in users if u.role == "OWNER"), users[0])
        cashier = next((u for u in users if u.role == "CASHIER"), owner)
        cashiers = [owner.id, cashier.id]

        products = (await db.execute(
            select(Product).where(Product.tenant_id == tid, Product.deleted_at.is_(None))
        )).scalars().all()
        if not products:
            print("❌ Không có sản phẩm. Chạy seed_sqlite.py trước.")
            return

        customers = (await db.execute(
            select(Customer).where(Customer.tenant_id == tid, Customer.deleted_at.is_(None))
        )).scalars().all()

        # Tồn kho hiện tại + giá vốn vào bộ nhớ
        inv_rows = (await db.execute(
            select(Inventory).where(Inventory.tenant_id == tid)
        )).scalars().all()
        inv_by_pid = {r.product_id: r for r in inv_rows}
        for p in products:
            if p.id not in inv_by_pid:
                row = Inventory(tenant_id=tid, product_id=p.id, quantity=D(0))
                db.add(row)
                inv_by_pid[p.id] = row
        await db.flush()

        qty: dict[int, Decimal] = {p.id: D(inv_by_pid[p.id].quantity) for p in products}
        cost: dict[int, Decimal] = {p.id: D(p.cost_price) for p in products}
        prod_by_id = {p.id: p for p in products}

        cg = CodeGen()
        # Nạp bộ đếm từ mã đã tồn tại để tránh trùng UNIQUE(tenant_id, code)
        existing_codes = []
        for model in (Invoice, GoodsReceipt, ReturnOrder, CashTransaction):
            existing_codes += (await db.execute(
                select(model.code).where(model.tenant_id == tid)
            )).scalars().all()
        cg.seed_from_codes(existing_codes)

        start = (datetime.now(VN_TZ) - timedelta(days=N_DAYS - 1)).date()
        receipt_offsets = {1, 8, 15, 22, 27}  # ngày nhập hàng trong tháng

        stats = {"receipts": 0, "invoices": 0, "items": 0, "returns": 0,
                 "cash_in": 0, "cash_out": 0, "debt_invoices": 0}
        recent_completed: list[Invoice] = []

        for offset in range(N_DAYS):
            day = start + timedelta(days=offset)
            weekday = day.weekday()  # 0=Mon .. 6=Sun
            is_weekend = weekday >= 5

            # ── Nhập hàng định kỳ (sáng sớm) ──────────────────────────────
            if offset in receipt_offsets:
                await _make_receipt(
                    db, tid, owner.id, cg, at(day, 7, 30),
                    products, qty, cost, inv_by_pid, stats,
                )

            # ── Hóa đơn bán hàng trong ngày ───────────────────────────────
            n_inv = random.randint(14, 22) if is_weekend else random.randint(7, 14)
            hours = sorted(random.sample(range(7, 21), k=min(n_inv, 14)))
            for i in range(n_inv):
                hour = hours[i] if i < len(hours) else random.randint(7, 20)
                minute = random.randint(0, 59)
                ts = at(day, hour, minute)
                inv = await _make_invoice(
                    db, tid, random.choice(cashiers), cg, ts,
                    products, customers, qty, cost, prod_by_id, inv_by_pid, stats,
                )
                if inv is not None:
                    recent_completed.append(inv)

            # ── Trả hàng lác đác (mỗi ~5 ngày) ────────────────────────────
            if offset % 5 == 3 and recent_completed:
                src = random.choice(recent_completed[-30:])
                await _make_return(
                    db, tid, random.choice(cashiers), cg, at(day, 16, 0),
                    src, qty, inv_by_pid, prod_by_id, stats,
                )

            # ── Chi phí vận hành ──────────────────────────────────────────
            if weekday == 0:  # thứ 2: tiền điện/nước/vận hành
                await _make_cash_out(db, tid, owner.id, cg, at(day, 18, 0),
                                     "OPERATING", random.choice([180_000, 250_000, 320_000]),
                                     "Chi phí điện nước / vận hành", stats)
            if offset in (5, 19):  # 2 kỳ lương trong tháng
                await _make_cash_out(db, tid, owner.id, cg, at(day, 19, 0),
                                     "SALARY", 4_500_000, "Lương nhân viên", stats)

        # ── Đồng bộ cache tồn kho + CodeSequence ──────────────────────────
        for pid, row in inv_by_pid.items():
            row.quantity = q3(qty[pid])
        for p in products:
            p.cost_price = money(cost[p.id])

        for (prefix, date_part), last in cg.counters.items():
            seq = (await db.execute(
                select(CodeSequence).where(
                    CodeSequence.tenant_id == tid,
                    CodeSequence.prefix == prefix,
                    CodeSequence.date_part == date_part,
                )
            )).scalar_one_or_none()
            if seq is None:
                db.add(CodeSequence(tenant_id=tid, prefix=prefix,
                                    date_part=date_part, last_number=last))
            else:
                seq.last_number = max(seq.last_number, last)

        await db.commit()

    await engine.dispose()

    print("\n" + "─" * 52)
    print("✅ Seed 1 tháng hoạt động hoàn tất!")
    for k in ("receipts", "invoices", "items", "debt_invoices", "returns", "cash_in", "cash_out"):
        print(f"   {k:14}: {stats[k]}")
    print(f"   DB            : {DB_URL}")
    print("─" * 52)


# ──────────────────────────────────────────────────────────────────────────
async def _make_receipt(db, tid, uid, cg, ts, products, qty, cost, inv_by_pid, stats):
    n = random.randint(20, 40)
    chosen = random.sample(products, k=min(n, len(products)))
    receipt = GoodsReceipt(
        tenant_id=tid, code=cg.next("NK", ts), supplier_id=None,
        total=D(0), paid_amount=D(0), status="COMPLETED",
        note="Nhập hàng định kỳ (seed)", completed_at=ts,
        created_at=ts, updated_at=ts, created_by=uid,
    )
    db.add(receipt)
    await db.flush()

    total = D(0)
    for p in chosen:
        in_qty = D(random.randint(10, 60))
        # giá nhập dao động quanh giá vốn hiện tại ±8%
        base = cost[p.id] if cost[p.id] > 0 else D(p.cost_price)
        in_cost = money(base * D(random.uniform(0.96, 1.08)))
        line_total = money(in_qty * in_cost)
        total += line_total
        db.add(GoodsReceiptItem(
            receipt_id=receipt.id, product_id=p.id, quantity=in_qty,
            cost_price=in_cost, line_total=line_total, unit_name=p.unit,
            conversion_rate=D(1),
        ))

        # giá vốn bình quân (theo CLAUDE.md)
        old_stock = qty[p.id]
        old_cost = cost[p.id]
        if old_stock <= 0:
            new_cost = in_cost
        else:
            new_cost = money((old_stock * old_cost + in_qty * in_cost) / (old_stock + in_qty))
        if new_cost != old_cost:
            db.add(PriceHistory(
                tenant_id=tid, product_id=p.id, field="cost_price",
                old_value=old_cost, new_value=new_cost,
                ref_type="GOODS_RECEIPT", ref_id=receipt.id,
                changed_at=ts, changed_by=uid,
            ))
            cost[p.id] = new_cost

        new_balance = q3(old_stock + in_qty)
        db.add(StockMovement(
            tenant_id=tid, product_id=p.id, quantity=in_qty, unit_cost=in_cost,
            type="RECEIPT", ref_type="GOODS_RECEIPT", ref_id=receipt.id,
            balance_after=new_balance, created_at=ts, created_by=uid,
        ))
        qty[p.id] = new_balance

    receipt.total = money(total)
    receipt.paid_amount = money(total)  # trả đủ NCC
    db.add(CashTransaction(
        tenant_id=tid, code=cg.next("PC", ts), direction="OUT", method="BANK_TRANSFER",
        category="PURCHASE", amount=money(total), ref_type="GOODS_RECEIPT",
        ref_id=receipt.id, note=f"Trả tiền nhập hàng {receipt.code}",
        status="ACTIVE", created_at=ts, created_by=uid,
    ))
    stats["receipts"] += 1
    stats["cash_out"] += 1


async def _make_invoice(db, tid, uid, cg, ts, products, customers,
                        qty, cost, prod_by_id, inv_by_pid, stats):
    # chọn các SP còn tồn
    avail = [p for p in products if qty[p.id] >= 1]
    if not avail:
        return None
    n_lines = random.randint(1, 5)
    picked = random.sample(avail, k=min(n_lines, len(avail)))

    subtotal = D(0)
    discount_total = D(0)
    cost_total = D(0)
    items_data = []
    for p in picked:
        max_q = int(qty[p.id])
        if max_q < 1:
            continue
        if p.unit in ("kg", "lạng", "lít"):
            line_qty = q3(D(random.choice([0.5, 1, 1.5, 2, 2.5, 3])))
            line_qty = q3(min(line_qty, qty[p.id]))
        else:
            line_qty = D(random.randint(1, min(5, max_q)))
        unit_price = money(D(p.sale_price))
        line_base = money(line_qty * unit_price)
        # giảm giá lác đác
        line_disc = D(0)
        if random.random() < 0.12:
            line_disc = money(min(line_base, D(random.choice([1000, 2000, 5000]))))
        line_total = money(line_base - line_disc)
        subtotal += line_base
        discount_total += line_disc
        cost_total += money(line_qty * cost[p.id])
        items_data.append((p, line_qty, unit_price, line_disc, line_total))

    if not items_data:
        return None

    total = money(subtotal - discount_total)
    customer = random.choice(customers) if (customers and random.random() < 0.55) else None

    # thanh toán: phần lớn trả đủ; ~10% (có KH) bán nợ
    is_debt = customer is not None and random.random() < 0.18
    method = "BANK_TRANSFER" if random.random() < 0.22 else "CASH"
    if is_debt:
        paid = money(total * D(random.choice([0, 0.3, 0.5])))
        change = D(0)
        stats["debt_invoices"] += 1
    else:
        if method == "CASH":
            paid = money(total + D(random.choice([0, 0, 0, 2000, 5000, 10000])))
        else:
            paid = total
        change = money(max(D(0), paid - total))

    code = cg.next("HD", ts)
    invoice = Invoice(
        tenant_id=tid, code=code, customer_id=(customer.id if customer else None),
        cashier_id=uid, subtotal=money(subtotal), discount_amount=money(discount_total),
        total=total, cost_total=money(cost_total), paid_amount=paid, change_amount=change,
        status="COMPLETED", note=None, completed_at=ts,
        created_at=ts, updated_at=ts, created_by=uid,
    )
    db.add(invoice)
    await db.flush()

    for p, line_qty, unit_price, line_disc, line_total in items_data:
        db.add(InvoiceItem(
            invoice_id=invoice.id, product_id=p.id, product_name=p.name,
            product_sku=p.sku, unit=p.unit, quantity=line_qty, unit_price=unit_price,
            cost_price=money(cost[p.id]), discount_amount=line_disc, line_total=line_total,
            unit_id=None, conversion_rate=D(1),
        ))
        new_balance = q3(qty[p.id] - line_qty)
        db.add(StockMovement(
            tenant_id=tid, product_id=p.id, quantity=q3(-line_qty),
            unit_cost=money(cost[p.id]), type="SALE", ref_type="INVOICE",
            ref_id=invoice.id, balance_after=new_balance, created_at=ts, created_by=uid,
        ))
        qty[p.id] = new_balance
        stats["items"] += 1

    if paid > 0:
        db.add(Payment(invoice_id=invoice.id, method=method, amount=paid,
                       note=None, created_at=ts))
        db.add(CashTransaction(
            tenant_id=tid, code=cg.next("PT", ts), direction="IN",
            method=("BANK_TRANSFER" if method == "BANK_TRANSFER" else "CASH"),
            category="SALE", amount=paid, ref_type="INVOICE", ref_id=invoice.id,
            partner_type=("CUSTOMER" if customer else None),
            partner_id=(customer.id if customer else None),
            note=f"Thu tiền hóa đơn {code}", status="ACTIVE",
            created_at=ts, created_by=uid,
        ))
        stats["cash_in"] += 1
    if change > 0:
        db.add(CashTransaction(
            tenant_id=tid, code=cg.next("PC", ts), direction="OUT", method="CASH",
            category="CHANGE", amount=change, ref_type="INVOICE", ref_id=invoice.id,
            note=f"Tiền thối hóa đơn {code}", status="ACTIVE",
            created_at=ts, created_by=uid,
        ))
        stats["cash_out"] += 1

    if customer:
        customer.total_spent = money(D(customer.total_spent) + total)
        customer.total_orders = (customer.total_orders or 0) + 1
        customer.last_order_at = ts

    stats["invoices"] += 1
    return invoice


async def _make_return(db, tid, uid, cg, ts, src_invoice, qty, inv_by_pid, prod_by_id, stats):
    items = (await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == src_invoice.id)
    )).scalars().all()
    if not items:
        return
    it = random.choice(items)
    ret_qty = q3(min(D(it.quantity), D(1)))  # trả tối đa 1 đơn vị
    if ret_qty <= 0:
        return
    unit_price = D(it.unit_price)
    line_total = money(ret_qty * unit_price)
    cost_price = D(it.cost_price)

    ro = ReturnOrder(
        tenant_id=tid, code=cg.next("TH", ts), invoice_id=src_invoice.id,
        customer_id=src_invoice.customer_id, customer_name=None, cashier_id=uid,
        subtotal=line_total, total_refund=line_total, debt_adjust=D(0),
        cash_refund=line_total, cost_total=money(ret_qty * cost_price),
        refund_method="CASH", status="COMPLETED", reason="Khách đổi/trả hàng (seed)",
        completed_at=ts, created_at=ts, updated_at=ts, created_by=uid,
    )
    db.add(ro)
    await db.flush()

    db.add(ReturnOrderItem(
        return_id=ro.id, invoice_item_id=it.id, product_id=it.product_id,
        product_name=it.product_name, product_sku=it.product_sku, quantity=ret_qty,
        unit_price=unit_price, cost_price=cost_price, line_total=line_total,
        unit_id=None, conversion_rate=D(1),
    ))
    new_balance = q3(qty.get(it.product_id, D(0)) + ret_qty)
    db.add(StockMovement(
        tenant_id=tid, product_id=it.product_id, quantity=ret_qty, unit_cost=cost_price,
        type="RETURN", ref_type="SALES_RETURN", ref_id=ro.id,
        balance_after=new_balance, created_at=ts, created_by=uid,
        note=f"Trả hàng {ro.code}",
    ))
    qty[it.product_id] = new_balance

    db.add(CashTransaction(
        tenant_id=tid, code=cg.next("PC", ts), direction="OUT", method="CASH",
        category="REFUND", amount=line_total, ref_type="SALES_RETURN", ref_id=ro.id,
        partner_type=("CUSTOMER" if src_invoice.customer_id else None),
        partner_id=src_invoice.customer_id,
        note=f"Hoàn tiền trả hàng {ro.code}", status="ACTIVE",
        created_at=ts, created_by=uid,
    ))
    stats["returns"] += 1
    stats["cash_out"] += 1


async def _make_cash_out(db, tid, uid, cg, ts, category, amount, note, stats):
    db.add(CashTransaction(
        tenant_id=tid, code=cg.next("PC", ts), direction="OUT", method="CASH",
        category=category, amount=money(D(amount)), ref_type="MANUAL", ref_id=None,
        note=note, status="ACTIVE", created_at=ts, created_by=uid,
    ))
    stats["cash_out"] += 1


if __name__ == "__main__":
    asyncio.run(main())
