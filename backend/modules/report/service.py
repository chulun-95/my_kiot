from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.inventory.models import Inventory, GoodsReceipt
from backend.modules.product.models import Product
from backend.modules.sales.models import Invoice, InvoiceItem, ReturnOrder, ReturnOrderItem
from backend.modules.customer.models import Customer, Supplier
from backend.modules.cashbook.models import CashTransaction


# ====================================================================
# Helpers
# ====================================================================

def _today_range() -> tuple[datetime, datetime]:
    """Return [start, end) for today in UTC (giản lược — sẽ chuyển TZ khi cần)."""
    now = datetime.now(tz=timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _date_range(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(to_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    return start, end


async def _returns_totals(db: AsyncSession, tenant_id: int, start: datetime, end: datetime) -> tuple[Decimal, Decimal, int]:
    """Aggregate refund and cost from completed returns in date range."""
    row = (await db.execute(
        select(
            func.coalesce(func.sum(ReturnOrder.total_refund), 0),
            func.coalesce(func.sum(ReturnOrder.cost_total), 0),
            func.count(ReturnOrder.id),
        ).where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        )
    )).one()
    return Decimal(str(row[0] or 0)), Decimal(str(row[1] or 0)), int(row[2] or 0)


async def _returns_by_product(db: AsyncSession, tenant_id: int, start: datetime, end: datetime) -> dict[int, tuple[Decimal, Decimal, Decimal]]:
    """Returns by product_id: (qty_base, revenue, cost)."""
    rate = func.coalesce(ReturnOrderItem.conversion_rate, 1)
    rows = (await db.execute(
        select(
            ReturnOrderItem.product_id,
            func.coalesce(func.sum(ReturnOrderItem.quantity * rate), 0),
            func.coalesce(func.sum(ReturnOrderItem.line_total), 0),
            func.coalesce(func.sum(ReturnOrderItem.cost_price * ReturnOrderItem.quantity * rate), 0),
        )
        .join(ReturnOrder, ReturnOrder.id == ReturnOrderItem.return_id)
        .where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        )
        .group_by(ReturnOrderItem.product_id)
    )).all()
    return {
        pid: (Decimal(str(q or 0)), Decimal(str(rev or 0)), Decimal(str(cost or 0)))
        for pid, q, rev, cost in rows
    }


async def _returns_by_period(db: AsyncSession, tenant_id: int, start: datetime, end: datetime, dialect: str, group_by: str) -> dict[str, tuple[Decimal, Decimal]]:
    """Returns by period: (refund, cost)."""
    if dialect == "postgresql":
        period_expr = func.to_char(ReturnOrder.completed_at, "YYYY-MM-DD" if group_by == "day" else "YYYY-MM")
    else:
        period_expr = func.strftime("%Y-%m-%d" if group_by == "day" else "%Y-%m", ReturnOrder.completed_at)
    rows = (await db.execute(
        select(
            period_expr.label("period"),
            func.coalesce(func.sum(ReturnOrder.total_refund), 0),
            func.coalesce(func.sum(ReturnOrder.cost_total), 0),
        ).where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        ).group_by("period")
    )).all()
    return {p: (Decimal(str(r or 0)), Decimal(str(c or 0))) for p, r, c in rows}


# ====================================================================
# Dashboard
# ====================================================================

async def dashboard(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    today_start, today_end = _today_range()

    # Today revenue + invoice count + profit
    today_q = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total), 0),
            func.coalesce(func.sum(Invoice.cost_total), 0),
            func.count(Invoice.id),
            func.count(func.distinct(Invoice.customer_id)),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= today_start,
            Invoice.completed_at < today_end,
        )
    )
    row = today_q.one()
    today_revenue = Decimal(str(row[0] or 0))
    today_cost = Decimal(str(row[1] or 0))
    today_invoices = int(row[2] or 0)
    today_customers = int(row[3] or 0)

    # Deduct returns
    ret_refund, ret_cost, _ = await _returns_totals(db, tenant_id, today_start, today_end)
    today_revenue = today_revenue - ret_refund
    today_profit = today_revenue - (today_cost - ret_cost)

    # Pending drafts
    drafts_q = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id, Invoice.status == "DRAFT"
        )
    )
    pending_drafts = int(drafts_q.scalar() or 0)

    # Low stock — tách ra OUT_OF_STOCK (qty <= 0) vs LOW (0 < qty <= min)
    # Anchor trên Product + LEFT JOIN: SP chưa từng nhập kho (không có dòng
    # inventory) vẫn phải tính là hết hàng. Filter tenant của Inventory đặt
    # trong ON-clause để giữ outer join.
    qty_col = func.coalesce(Inventory.quantity, 0)
    low_q = await db.execute(
        select(qty_col)
        .select_from(Product)
        .outerjoin(
            Inventory,
            (Inventory.product_id == Product.id)
            & (Inventory.tenant_id == tenant_id),
        )
        .where(
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
            Product.status == "ACTIVE",
            Product.min_stock > 0,
            qty_col <= Product.min_stock,
        )
    )
    low_rows = low_q.all()
    out_of_stock_count = sum(1 for (q,) in low_rows if (q or 0) <= 0)
    low_stock_count = len(low_rows)

    # Inventory value: sum(inventory.quantity * product.cost_price)
    inv_value_q = await db.execute(
        select(
            func.coalesce(
                func.sum(Inventory.quantity * Product.cost_price), 0
            )
        )
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    inventory_value = Decimal(str(inv_value_q.scalar() or 0))

    return {
        "today_revenue": today_revenue,
        "today_invoices": today_invoices,
        "today_profit": today_profit,
        "today_customers": today_customers,
        "pending_drafts": pending_drafts,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "inventory_value": inventory_value,
    }


# ====================================================================
# Revenue
# ====================================================================

async def revenue(
    db: AsyncSession,
    tenant_id: int,
    from_date: date,
    to_date: date,
    group_by: str = "day",
) -> dict[str, Any]:
    if group_by not in {"day", "month"}:
        group_by = "day"

    start, end = _date_range(from_date, to_date)

    # Total
    total_q = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total), 0),
            func.coalesce(func.sum(Invoice.cost_total), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
    )
    row = total_q.one()
    total_revenue = Decimal(str(row[0] or 0))
    total_cost = Decimal(str(row[1] or 0))
    total_invoices = int(row[2] or 0)

    # Deduct returns
    r_refund, r_cost, _ = await _returns_totals(db, tenant_id, start, end)
    total_revenue = total_revenue - r_refund
    total_profit = total_revenue - (total_cost - r_cost)

    # Series — strftime works on both PG (with to_char) and SQLite.
    # Dùng SQLAlchemy's func.strftime cho SQLite; với PG có thể cần substr.
    # Để portable cho dev/test, dùng substr trên cast text.
    fmt = "%Y-%m-%d" if group_by == "day" else "%Y-%m"

    bind = db.bind
    dialect = bind.dialect.name if bind is not None else "sqlite"
    if dialect == "postgresql":
        if group_by == "day":
            period_expr = func.to_char(Invoice.completed_at, "YYYY-MM-DD")
        else:
            period_expr = func.to_char(Invoice.completed_at, "YYYY-MM")
    else:
        # SQLite (test) — strftime
        period_expr = func.strftime(fmt, Invoice.completed_at)

    series_q = await db.execute(
        select(
            period_expr.label("period"),
            func.coalesce(func.sum(Invoice.total), 0).label("revenue"),
            func.coalesce(func.sum(Invoice.cost_total), 0).label("cost"),
            func.count(Invoice.id).label("invoices"),
        )
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
        .group_by("period")
        .order_by("period")
    )

    # Get returns by period
    rmap = await _returns_by_period(db, tenant_id, start, end, dialect, group_by)

    series = []
    for r in series_q.all():
        revenue = Decimal(str(r.revenue or 0))
        cost = Decimal(str(r.cost or 0))
        rr, rc = rmap.get(r.period, (Decimal("0"), Decimal("0")))
        net_revenue = revenue - rr
        series.append({
            "period": r.period,
            "revenue": net_revenue,
            "invoices": int(r.invoices or 0),
            "profit": net_revenue - (cost - rc),
        })

    return {
        "from_date": from_date,
        "to_date": to_date,
        "group_by": group_by,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_invoices": total_invoices,
        "series": series,
    }


# ====================================================================
# Top products
# ====================================================================

async def top_products(
    db: AsyncSession,
    tenant_id: int,
    from_date: date,
    to_date: date,
    limit: int = 10,
) -> dict[str, Any]:
    start, end = _date_range(from_date, to_date)
    limit = max(1, min(limit, 100))

    rate = func.coalesce(InvoiceItem.conversion_rate, 1)
    q = await db.execute(
        select(
            InvoiceItem.product_id,
            InvoiceItem.product_sku,
            InvoiceItem.product_name,
            func.sum(InvoiceItem.quantity * rate).label("qty"),
            func.sum(InvoiceItem.line_total).label("revenue"),
            func.sum(InvoiceItem.cost_price * InvoiceItem.quantity * rate).label("cost"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
        .group_by(
            InvoiceItem.product_id,
            InvoiceItem.product_sku,
            InvoiceItem.product_name,
        )
        .order_by(func.sum(InvoiceItem.line_total).desc())
        .limit(limit)
    )

    # Get returns by product
    rbp = await _returns_by_product(db, tenant_id, start, end)

    items = []
    for r in q.all():
        revenue = Decimal(str(r.revenue or 0))
        cost = Decimal(str(r.cost or 0))
        rq, rrev, rcost = rbp.get(r.product_id, (Decimal("0"), Decimal("0"), Decimal("0")))
        net_revenue = revenue - rrev
        items.append(
            {
                "product_id": r.product_id,
                "product_sku": r.product_sku,
                "product_name": r.product_name,
                "quantity_sold": Decimal(str(r.qty or 0)) - rq,
                "revenue": net_revenue,
                "profit": net_revenue - (cost - rcost),
            }
        )

    return {"from_date": from_date, "to_date": to_date, "items": items}


# ====================================================================
# Profit
# ====================================================================

async def profit(
    db: AsyncSession,
    tenant_id: int,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    start, end = _date_range(from_date, to_date)

    q = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total), 0),
            func.coalesce(func.sum(Invoice.cost_total), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
    )
    row = q.one()
    total_revenue = Decimal(str(row[0] or 0))
    total_cost = Decimal(str(row[1] or 0))
    invoices = int(row[2] or 0)

    # Deduct returns
    r_refund, r_cost, _ = await _returns_totals(db, tenant_id, start, end)
    total_revenue = total_revenue - r_refund
    total_cost = total_cost - r_cost

    return {
        "from_date": from_date,
        "to_date": to_date,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "gross_profit": total_revenue - total_cost,
        "invoices": invoices,
    }


# ====================================================================
# Stock summary
# ====================================================================

async def stock_summary(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    # Total active products
    total_q = await db.execute(
        select(func.count(Product.id)).where(
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    total_products = int(total_q.scalar() or 0)

    # In stock vs out of stock
    rows = (
        await db.execute(
            select(Inventory.quantity)
            .join(Product, Product.id == Inventory.product_id)
            .where(
                Inventory.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
            )
        )
    ).all()
    in_stock = sum(1 for (q,) in rows if (q or 0) > 0)
    out_of_stock = total_products - in_stock

    # Low stock
    low_q = await db.execute(
        select(func.count(Inventory.id))
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
            Product.status == "ACTIVE",
            Product.min_stock > 0,
            Inventory.quantity <= Product.min_stock,
        )
    )
    low_stock_count = int(low_q.scalar() or 0)

    # Inventory value
    inv_value_q = await db.execute(
        select(
            func.coalesce(
                func.sum(Inventory.quantity * Product.cost_price), 0
            )
        )
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    total_value = Decimal(str(inv_value_q.scalar() or 0))

    return {
        "total_products": total_products,
        "products_in_stock": in_stock,
        "products_out_of_stock": out_of_stock,
        "low_stock_count": low_stock_count,
        "total_inventory_value": total_value,
        "last_updated": datetime.now(tz=timezone.utc),
    }


# ====================================================================
# Products sold (báo cáo SP đã bán) — phân trang + sort + lọc nhóm hàng
# ====================================================================


async def products_sold(
    db: AsyncSession,
    tenant_id: int,
    from_date: date,
    to_date: date,
    *,
    category_id: int | None = None,
    sort_by: str = "revenue",
    order: str = "desc",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    if sort_by not in {"revenue", "quantity", "profit"}:
        sort_by = "revenue"
    if order not in {"asc", "desc"}:
        order = "desc"
    page = max(1, page)
    limit = max(1, min(limit, 100))

    start, end = _date_range(from_date, to_date)

    rate = func.coalesce(InvoiceItem.conversion_rate, 1)
    qty_base = func.sum(InvoiceItem.quantity * rate)
    gross = func.sum(InvoiceItem.unit_price * InvoiceItem.quantity)
    disc = func.sum(InvoiceItem.discount_amount)
    net = func.sum(InvoiceItem.line_total)
    cost = func.sum(InvoiceItem.cost_price * InvoiceItem.quantity * rate)

    filters = [
        Invoice.tenant_id == tenant_id,
        Invoice.status == "COMPLETED",
        Invoice.completed_at >= start,
        Invoice.completed_at < end,
    ]

    def _with_scope(stmt):
        stmt = stmt.join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        if category_id is not None:
            stmt = stmt.join(Product, Product.id == InvoiceItem.product_id).where(
                Product.category_id == category_id
            )
        return stmt.where(*filters)

    grouped = _with_scope(
        select(
            InvoiceItem.product_id.label("product_id"),
            InvoiceItem.product_sku.label("product_sku"),
            InvoiceItem.product_name.label("product_name"),
            qty_base.label("quantity_sold"),
            gross.label("revenue"),
            disc.label("discount"),
            net.label("net_revenue"),
            cost.label("cost"),
        )
    ).group_by(
        InvoiceItem.product_id,
        InvoiceItem.product_sku,
        InvoiceItem.product_name,
    )

    # Tổng số SP (distinct) khớp bộ lọc — count số nhóm
    total = (
        await db.execute(select(func.count()).select_from(grouped.subquery()))
    ).scalar() or 0

    # Totals trên TOÀN BỘ (không group, không phân trang)
    totals_row = (
        await db.execute(
            _with_scope(
                select(
                    func.coalesce(qty_base, 0),
                    func.coalesce(gross, 0),
                    func.coalesce(disc, 0),
                    func.coalesce(net, 0),
                    func.coalesce(cost, 0),
                )
            )
        )
    ).one()
    t_qty = Decimal(str(totals_row[0] or 0))
    t_gross = Decimal(str(totals_row[1] or 0))
    t_disc = Decimal(str(totals_row[2] or 0))
    t_net = Decimal(str(totals_row[3] or 0))
    t_cost = Decimal(str(totals_row[4] or 0))

    sort_exprs = {"revenue": net, "quantity": qty_base, "profit": net - cost}
    sort_col = sort_exprs[sort_by]
    direction = sort_col.desc() if order == "desc" else sort_col.asc()

    page_rows = (
        await db.execute(
            grouped.order_by(direction, InvoiceItem.product_id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()

    # Get returns by product
    rbp = await _returns_by_product(db, tenant_id, start, end)

    items = []
    for r in page_rows:
        revenue = Decimal(str(r.revenue or 0))
        discount = Decimal(str(r.discount or 0))
        net_revenue = Decimal(str(r.net_revenue or 0))
        c = Decimal(str(r.cost or 0))
        rq, rrev, rcost = rbp.get(r.product_id, (Decimal("0"), Decimal("0"), Decimal("0")))
        qty = Decimal(str(r.quantity_sold or 0)) - rq
        net_rev = net_revenue - rrev
        cost = c - rcost
        prof = net_rev - cost
        margin = (
            (prof / net_rev * Decimal("100")).quantize(Decimal("0.01"))
            if net_rev > 0
            else Decimal("0")
        )
        items.append(
            {
                "product_id": r.product_id,
                "product_sku": r.product_sku,
                "product_name": r.product_name,
                "quantity_sold": qty,
                "revenue": revenue - rrev,
                "discount": discount,
                "net_revenue": net_rev,
                "cost": cost,
                "profit": prof,
                "margin_pct": margin,
            }
        )

    # Deduct returns from totals
    rate = func.coalesce(ReturnOrderItem.conversion_rate, 1)
    ret_totals_row = (await db.execute(
        select(
            func.coalesce(func.sum(ReturnOrderItem.quantity * rate), 0),
            func.coalesce(func.sum(ReturnOrderItem.line_total), 0),
            func.coalesce(func.sum(ReturnOrderItem.cost_price * ReturnOrderItem.quantity * rate), 0),
        )
        .join(ReturnOrder, ReturnOrder.id == ReturnOrderItem.return_id)
        .where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        )
    )).one()
    ret_qty = Decimal(str(ret_totals_row[0] or 0))
    ret_rev = Decimal(str(ret_totals_row[1] or 0))
    ret_cost = Decimal(str(ret_totals_row[2] or 0))

    t_qty_net = t_qty - ret_qty
    t_net_net = t_net - ret_rev
    t_cost_net = t_cost - ret_cost

    return {
        "from_date": from_date,
        "to_date": to_date,
        "sort_by": sort_by,
        "order": order,
        "category_id": category_id,
        "items": items,
        "totals": {
            "quantity_sold": t_qty_net,
            "revenue": t_gross - ret_rev,
            "discount": t_disc,
            "net_revenue": t_net_net,
            "cost": t_cost_net,
            "profit": t_net_net - t_cost_net,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": int(total),
            "total_pages": int(ceil(total / limit)) if total else 0,
        },
    }


# ====================================================================
# Debt Report
# ====================================================================

async def customer_debts(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    """Calculate customer debts: (total - paid) from COMPLETED invoices minus collected amounts."""
    # Nợ phát sinh = Σ(total - paid) hóa đơn COMPLETED, customer_id not null
    owed_rows = (await db.execute(
        select(
            Invoice.customer_id,
            func.coalesce(func.sum(Invoice.total - Invoice.paid_amount), 0),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.customer_id.isnot(None),
        ).group_by(Invoice.customer_id)
    )).all()
    owed = {cid: Decimal(str(v or 0)) for cid, v in owed_rows}

    # Đã thu nợ = Σ cash IN category=DEBT_COLLECTION ACTIVE, partner CUSTOMER
    coll_rows = (await db.execute(
        select(
            CashTransaction.partner_id,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.direction == "IN",
            CashTransaction.category == "DEBT_COLLECTION",
            CashTransaction.partner_type == "CUSTOMER",
            CashTransaction.partner_id.isnot(None),
        ).group_by(CashTransaction.partner_id)
    )).all()
    collected = {pid: Decimal(str(v or 0)) for pid, v in coll_rows}

    partner_ids = set(owed) | set(collected)
    debts: dict[int, Decimal] = {}
    for pid in partner_ids:
        d = owed.get(pid, Decimal("0")) - collected.get(pid, Decimal("0"))
        if d > 0:
            debts[pid] = d

    items = []
    if debts:
        crows = (await db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.id.in_(list(debts.keys())))
        )).scalars().all()
        cmap = {c.id: c for c in crows}
        for pid, d in sorted(debts.items(), key=lambda kv: kv[1], reverse=True):
            c = cmap.get(pid)
            items.append({
                "partner_id": pid,
                "partner_name": c.name if c else "Khách đã xóa",
                "phone": c.phone if c else None,
                "debt": d,
            })
    return {"items": items, "total_debt": sum((i["debt"] for i in items), Decimal("0"))}


async def supplier_debts(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    """Calculate supplier debts: (total - paid) from COMPLETED goods receipts minus paid amounts."""
    owed_rows = (await db.execute(
        select(
            GoodsReceipt.supplier_id,
            func.coalesce(func.sum(GoodsReceipt.total - GoodsReceipt.paid_amount), 0),
        ).where(
            GoodsReceipt.tenant_id == tenant_id,
            GoodsReceipt.status == "COMPLETED",
            GoodsReceipt.supplier_id.isnot(None),
        ).group_by(GoodsReceipt.supplier_id)
    )).all()
    owed = {sid: Decimal(str(v or 0)) for sid, v in owed_rows}

    paid_rows = (await db.execute(
        select(
            CashTransaction.partner_id,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.direction == "OUT",
            CashTransaction.category == "DEBT_PAYMENT",
            CashTransaction.partner_type == "SUPPLIER",
            CashTransaction.partner_id.isnot(None),
        ).group_by(CashTransaction.partner_id)
    )).all()
    paid = {pid: Decimal(str(v or 0)) for pid, v in paid_rows}

    partner_ids = set(owed) | set(paid)
    debts: dict[int, Decimal] = {}
    for pid in partner_ids:
        d = owed.get(pid, Decimal("0")) - paid.get(pid, Decimal("0"))
        if d > 0:
            debts[pid] = d

    items = []
    if debts:
        srows = (await db.execute(
            select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.id.in_(list(debts.keys())))
        )).scalars().all()
        smap = {s.id: s for s in srows}
        for pid, d in sorted(debts.items(), key=lambda kv: kv[1], reverse=True):
            s = smap.get(pid)
            items.append({
                "partner_id": pid,
                "partner_name": s.name if s else "NCC đã xóa",
                "phone": s.phone if s else None,
                "debt": d,
            })
    return {"items": items, "total_debt": sum((i["debt"] for i in items), Decimal("0"))}
