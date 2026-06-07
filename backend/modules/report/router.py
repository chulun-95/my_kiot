from __future__ import annotations
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_role
from backend.exceptions import AppError
from backend.modules.auth.models import User
from backend.modules.report import service as report_service
from backend.modules.report.schemas import (
    DashboardResponse,
    DebtItem,
    DebtReportResponse,
    ProductsSoldResponse,
    ProductsSoldSortBy,
    ProfitResponse,
    RevenuePoint,
    RevenueResponse,
    SortOrder,
    StockSummaryResponse,
    TopProductItem,
    TopProductsResponse,
)


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _default_range(from_date: date | None, to_date: date | None) -> tuple[date, date]:
    today = date.today()
    f = from_date or (today - timedelta(days=30))
    t = to_date or today
    if f > t:
        raise AppError(400, "INVALID_DATE_RANGE", "Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc")
    return f, t


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.dashboard(db, owner.current_tenant_id)
    return DashboardResponse(**data)


@router.get("/revenue", response_model=RevenueResponse)
async def revenue(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    group_by: str = Query(default="day"),
):
    f, t = _default_range(from_date, to_date)
    data = await report_service.revenue(
        db, owner.current_tenant_id, f, t, group_by=group_by
    )
    return RevenueResponse(
        from_date=data["from_date"],
        to_date=data["to_date"],
        group_by=data["group_by"],
        total_revenue=data["total_revenue"],
        total_profit=data["total_profit"],
        total_invoices=data["total_invoices"],
        series=[RevenuePoint(**p) for p in data["series"]],
    )


@router.get("/top-products", response_model=TopProductsResponse)
async def top_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=10, ge=1, le=100),
):
    f, t = _default_range(from_date, to_date)
    data = await report_service.top_products(
        db, owner.current_tenant_id, f, t, limit=limit
    )
    return TopProductsResponse(
        from_date=data["from_date"],
        to_date=data["to_date"],
        items=[TopProductItem(**i) for i in data["items"]],
    )


@router.get("/products-sold", response_model=ProductsSoldResponse)
async def products_sold(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    category_id: int | None = Query(default=None),
    sort_by: ProductsSoldSortBy = Query(default="revenue"),
    order: SortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    f, t = _default_range(from_date, to_date)
    data = await report_service.products_sold(
        db,
        owner.current_tenant_id,
        f,
        t,
        category_id=category_id,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )
    return ProductsSoldResponse(**data)


@router.get("/profit", response_model=ProfitResponse)
async def profit(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
):
    f, t = _default_range(from_date, to_date)
    data = await report_service.profit(db, owner.current_tenant_id, f, t)
    return ProfitResponse(**data)


@router.get("/stock-summary", response_model=StockSummaryResponse)
async def stock_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.stock_summary(db, owner.current_tenant_id)
    return StockSummaryResponse(**data)


@router.get("/debts/customers", response_model=DebtReportResponse)
async def customer_debts(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.customer_debts(db, owner.current_tenant_id)
    return DebtReportResponse(items=[DebtItem(**i) for i in data["items"]], total_debt=data["total_debt"])


@router.get("/debts/suppliers", response_model=DebtReportResponse)
async def supplier_debts(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.supplier_debts(db, owner.current_tenant_id)
    return DebtReportResponse(items=[DebtItem(**i) for i in data["items"]], total_debt=data["total_debt"])
