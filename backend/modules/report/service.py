from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.inventory.models import Inventory
from backend.modules.product.models import Product
from backend.modules.sales.models import Invoice, InvoiceItem


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
    today_profit = today_revenue - today_cost

    # Pending drafts
    drafts_q = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id, Invoice.status == "DRAFT"
        )
    )
    pending_drafts = int(drafts_q.scalar() or 0)

    # Low stock — tách ra OUT_OF_STOCK (qty <= 0) vs LOW (0 < qty <= min)
    low_q = await db.execute(
        select(Inventory.quantity)
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
            Product.status == "ACTIVE",
            Product.min_stock > 0,
            Inventory.quantity <= Product.min_stock,
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
    total_profit = total_revenue - total_cost

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

    series = [
        {
            "period": r.period,
            "revenue": Decimal(str(r.revenue or 0)),
            "invoices": int(r.invoices or 0),
            "profit": Decimal(str((r.revenue or 0))) - Decimal(str((r.cost or 0))),
        }
        for r in series_q.all()
    ]

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

    items = []
    for r in q.all():
        revenue = Decimal(str(r.revenue or 0))
        cost = Decimal(str(r.cost or 0))
        items.append(
            {
                "product_id": r.product_id,
                "product_sku": r.product_sku,
                "product_name": r.product_name,
                "quantity_sold": Decimal(str(r.qty or 0)),
                "revenue": revenue,
                "profit": revenue - cost,
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

    items = []
    for r in page_rows:
        revenue = Decimal(str(r.revenue or 0))
        discount = Decimal(str(r.discount or 0))
        net_revenue = Decimal(str(r.net_revenue or 0))
        c = Decimal(str(r.cost or 0))
        prof = net_revenue - c
        margin = (
            (prof / net_revenue * Decimal("100")).quantize(Decimal("0.01"))
            if net_revenue > 0
            else Decimal("0")
        )
        items.append(
            {
                "product_id": r.product_id,
                "product_sku": r.product_sku,
                "product_name": r.product_name,
                "quantity_sold": Decimal(str(r.quantity_sold or 0)),
                "revenue": revenue,
                "discount": discount,
                "net_revenue": net_revenue,
                "cost": c,
                "profit": prof,
                "margin_pct": margin,
            }
        )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "sort_by": sort_by,
        "order": order,
        "category_id": category_id,
        "items": items,
        "totals": {
            "quantity_sold": t_qty,
            "revenue": t_gross,
            "discount": t_disc,
            "net_revenue": t_net,
            "cost": t_cost,
            "profit": t_net - t_cost,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": int(total),
            "total_pages": int(ceil(total / limit)) if total else 0,
        },
    }
