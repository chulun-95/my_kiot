from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.customer.models import Customer
from backend.modules.inventory.models import Inventory, StockMovement
from backend.modules.product.models import Product
from backend.modules.sales.models import Invoice, InvoiceItem, Payment
from backend.modules.sales.schemas import (
    InvoiceCompleteRequest,
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
)
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate


# ====================================================================
# helpers
# ====================================================================

async def _get_invoice(
    db: AsyncSession,
    tenant_id: int,
    invoice_id: int,
    *,
    with_payments: bool = True,
) -> Invoice:
    opts = [selectinload(Invoice.items)]
    if with_payments:
        opts.append(selectinload(Invoice.payments))
    invoice = await db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        .options(*opts)
    )
    if not invoice:
        raise AppError(404, "INVOICE_NOT_FOUND", "Hóa đơn không tồn tại")
    return invoice


async def _validate_customer(
    db: AsyncSession, tenant_id: int, customer_id: int | None
) -> Customer | None:
    if customer_id is None:
        return None
    c = await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    )
    if not c:
        raise AppError(404, "CUSTOMER_NOT_FOUND", "Khách hàng không tồn tại")
    return c


async def _validate_products(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> dict[int, Product]:
    if not product_ids:
        return {}
    rows = (
        await db.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    by_id = {p.id: p for p in rows}
    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise AppError(
            404,
            "PRODUCT_NOT_FOUND",
            f"Sản phẩm không tồn tại: {missing}",
            {"missing_product_ids": missing},
        )
    return by_id


async def _lock_inventory_rows(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> dict[int, Inventory]:
    sorted_ids = sorted(set(product_ids))
    rows = (
        await db.execute(
            select(Inventory)
            .where(
                Inventory.tenant_id == tenant_id,
                Inventory.product_id.in_(sorted_ids),
            )
            .order_by(Inventory.product_id)
            .with_for_update()
        )
    ).scalars().all()
    by_pid = {r.product_id: r for r in rows}
    for pid in sorted_ids:
        if pid not in by_pid:
            row = Inventory(tenant_id=tenant_id, product_id=pid, quantity=Decimal("0"))
            db.add(row)
            await db.flush()
            by_pid[pid] = row
    return by_pid


def _compute_line(
    item, product: Product
) -> tuple[Decimal, Decimal]:
    unit_price = (
        item.unit_price if item.unit_price is not None else product.sale_price
    )
    line_subtotal = unit_price * item.quantity
    line_total = (line_subtotal - item.discount_amount).quantize(Decimal("0.01"))
    if line_total < 0:
        line_total = Decimal("0")
    return unit_price, line_total


# ====================================================================
# CRUD
# ====================================================================

async def create_invoice(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: InvoiceCreateRequest,
) -> Invoice:
    await _validate_customer(db, tenant_id, payload.customer_id)

    code = await generate_code(db, tenant_id, "HD", with_date=True)

    invoice = Invoice(
        tenant_id=tenant_id,
        code=code,
        customer_id=payload.customer_id,
        cashier_id=user_id,
        created_by=user_id,
        status="DRAFT",
        discount_amount=payload.discount_amount,
        note=payload.note,
    )

    subtotal = Decimal("0")
    if payload.items:
        product_ids = [it.product_id for it in payload.items]
        products = await _validate_products(db, tenant_id, product_ids)
        for it in payload.items:
            p = products[it.product_id]
            unit_price, line_total = _compute_line(it, p)
            invoice.items.append(
                InvoiceItem(
                    product_id=p.id,
                    product_name=p.name,
                    product_sku=p.sku,
                    unit=p.unit,
                    quantity=it.quantity,
                    unit_price=unit_price,
                    cost_price=p.cost_price,
                    discount_amount=it.discount_amount,
                    line_total=line_total,
                )
            )
            subtotal += line_total

    invoice.subtotal = subtotal
    invoice.total = max(Decimal("0"), subtotal - payload.discount_amount)

    db.add(invoice)
    await db.commit()
    return await _get_invoice(db, tenant_id, invoice.id)


async def update_invoice(
    db: AsyncSession,
    tenant_id: int,
    invoice_id: int,
    payload: InvoiceUpdateRequest,
) -> Invoice:
    invoice = await _get_invoice(db, tenant_id, invoice_id)
    if invoice.status != "DRAFT":
        raise AppError(
            400, "INVOICE_NOT_DRAFT", "Chỉ sửa được hóa đơn nháp"
        )

    if payload.customer_id is not None:
        await _validate_customer(db, tenant_id, payload.customer_id)
        invoice.customer_id = payload.customer_id
    if payload.note is not None:
        invoice.note = payload.note
    if payload.discount_amount is not None:
        invoice.discount_amount = payload.discount_amount

    if payload.items is not None:
        product_ids = [it.product_id for it in payload.items]
        products = await _validate_products(db, tenant_id, product_ids)

        invoice.items.clear()
        await db.flush()

        subtotal = Decimal("0")
        for it in payload.items:
            p = products[it.product_id]
            unit_price, line_total = _compute_line(it, p)
            invoice.items.append(
                InvoiceItem(
                    product_id=p.id,
                    product_name=p.name,
                    product_sku=p.sku,
                    unit=p.unit,
                    quantity=it.quantity,
                    unit_price=unit_price,
                    cost_price=p.cost_price,
                    discount_amount=it.discount_amount,
                    line_total=line_total,
                )
            )
            subtotal += line_total
        invoice.subtotal = subtotal

    invoice.total = max(Decimal("0"), invoice.subtotal - invoice.discount_amount)

    await db.commit()
    return await _get_invoice(db, tenant_id, invoice.id)


# ====================================================================
# COMPLETE — luồng quan trọng nhất
# ====================================================================

async def complete_invoice(
    db: AsyncSession,
    tenant_id: int,
    invoice_id: int,
    user_id: int,
    payload: InvoiceCompleteRequest,
) -> Invoice:
    invoice = await _get_invoice(db, tenant_id, invoice_id)
    if invoice.status != "DRAFT":
        raise AppError(
            400, "INVOICE_NOT_DRAFT", "Hóa đơn không ở trạng thái nháp"
        )
    if not invoice.items:
        raise AppError(
            400, "INVOICE_NO_ITEMS", "Hóa đơn chưa có sản phẩm"
        )

    # 1. Validate thanh toán
    total_paid = sum((p.amount for p in payload.payments), Decimal("0"))
    if total_paid < invoice.total and not payload.allow_debt:
        raise AppError(
            400,
            "INSUFFICIENT_PAYMENT",
            f"Thanh toán {total_paid} < tổng {invoice.total}",
            {"total": str(invoice.total), "paid": str(total_paid)},
        )

    # 2. Lock inventory + lấy product fresh
    product_ids = list({it.product_id for it in invoice.items})
    products = await _validate_products(db, tenant_id, product_ids)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    # 3. Kiểm tra tồn — gom toàn bộ thiếu
    qty_needed: dict[int, Decimal] = {}
    for item in invoice.items:
        qty_needed[item.product_id] = qty_needed.get(item.product_id, Decimal("0")) + item.quantity

    shortages = []
    for pid, need in qty_needed.items():
        product = products[pid]
        have = inv_by_pid[pid].quantity
        if have < need and not product.allow_negative:
            shortages.append({
                "product_id": pid,
                "product_name": product.name,
                "need": str(need),
                "have": str(have),
            })
    if shortages:
        raise AppError(
            400,
            "INSUFFICIENT_STOCK",
            "Không đủ tồn kho",
            {"shortages": shortages},
        )

    # 4. Cập nhật snapshot giá vốn TẠI THỜI ĐIỂM COMPLETE
    cost_total = Decimal("0")
    for item in invoice.items:
        p = products[item.product_id]
        item.cost_price = p.cost_price
        cost_total += (item.cost_price * item.quantity).quantize(Decimal("0.01"))
    invoice.cost_total = cost_total

    # 5. Trạng thái + tiền
    invoice.status = "COMPLETED"
    invoice.completed_at = datetime.now(tz=timezone.utc)
    invoice.paid_amount = total_paid
    invoice.change_amount = max(Decimal("0"), total_paid - invoice.total)

    # 6. Lưu payments
    for p in payload.payments:
        invoice.payments.append(
            Payment(method=p.method, amount=p.amount, note=p.note)
        )

    # 7. Trừ tồn + ghi kardex
    for pid in sorted(qty_needed.keys()):
        inv = inv_by_pid[pid]
        qty = qty_needed[pid]
        new_balance = inv.quantity - qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)

        # Tìm cost của line tương ứng (xấp xỉ — dùng snapshot product hiện tại)
        unit_cost = products[pid].cost_price

        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=-qty,
                unit_cost=unit_cost,
                type="SALE",
                ref_type="INVOICE",
                ref_id=invoice.id,
                balance_after=new_balance,
                created_by=user_id,
            )
        )

    # 8. Cập nhật thống kê KH
    if invoice.customer_id:
        c = await db.get(Customer, invoice.customer_id)
        if c:
            c.total_spent = (c.total_spent or Decimal("0")) + invoice.total
            c.total_orders = (c.total_orders or 0) + 1
            c.last_order_at = datetime.now(tz=timezone.utc)

    await db.commit()
    return await _get_invoice(db, tenant_id, invoice.id)


# ====================================================================
# CANCEL
# ====================================================================

async def cancel_invoice(
    db: AsyncSession,
    tenant_id: int,
    invoice_id: int,
    user_id: int,
    reason: str | None = None,
) -> Invoice:
    invoice = await _get_invoice(db, tenant_id, invoice_id)

    if invoice.status == "CANCELLED":
        raise AppError(400, "ALREADY_CANCELLED", "Hóa đơn đã bị hủy")

    if invoice.status == "DRAFT":
        invoice.status = "CANCELLED"
        invoice.cancelled_at = datetime.now(tz=timezone.utc)
        invoice.cancelled_by = user_id
        invoice.cancel_reason = reason
        await db.commit()
        return await _get_invoice(db, tenant_id, invoice.id)

    # COMPLETED → bút toán ngược
    product_ids = list({it.product_id for it in invoice.items})
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    qty_by_pid: dict[int, Decimal] = {}
    for it in invoice.items:
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + it.quantity

    for pid in sorted(qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        qty = qty_by_pid[pid]
        new_balance = inv.quantity + qty
        inv.quantity = new_balance
        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=qty,
                type="CANCEL_SALE",
                ref_type="INVOICE",
                ref_id=invoice.id,
                balance_after=new_balance,
                created_by=user_id,
                note=f"Hủy hóa đơn: {reason or ''}",
            )
        )

    invoice.status = "CANCELLED"
    invoice.cancelled_at = datetime.now(tz=timezone.utc)
    invoice.cancelled_by = user_id
    invoice.cancel_reason = reason

    # Trừ ngược thống kê KH
    if invoice.customer_id:
        c = await db.get(Customer, invoice.customer_id)
        if c:
            c.total_spent = max(Decimal("0"), (c.total_spent or Decimal("0")) - invoice.total)
            c.total_orders = max(0, (c.total_orders or 0) - 1)

    await db.commit()
    return await _get_invoice(db, tenant_id, invoice.id)


# ====================================================================
# QUERY
# ====================================================================

async def get_invoice(
    db: AsyncSession, tenant_id: int, invoice_id: int
) -> Invoice:
    return await _get_invoice(db, tenant_id, invoice_id)


async def list_invoices(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    customer_id: int | None = None,
    cashier_id: int | None = None,
) -> dict[str, Any]:
    stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if customer_id is not None:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if cashier_id is not None:
        stmt = stmt.where(Invoice.cashier_id == cashier_id)
    stmt = stmt.order_by(Invoice.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


async def list_drafts(
    db: AsyncSession, tenant_id: int, cashier_id: int | None = None
) -> list[Invoice]:
    stmt = select(Invoice).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status == "DRAFT",
    )
    if cashier_id is not None:
        stmt = stmt.where(Invoice.cashier_id == cashier_id)
    stmt = stmt.order_by(Invoice.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())
