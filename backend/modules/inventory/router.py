from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_role
from backend.modules.auth.models import User
from backend.modules.customer.models import Supplier
from backend.modules.inventory import service as inv_service
from backend.modules.inventory.schemas import (
    AdjustmentCreateRequest,
    AdjustmentMovementResponse,
    AdjustmentMovementsResponse,
    AdjustmentResponse,
    AdjustmentResultItem,
    GoodsReceiptBriefResponse,
    GoodsReceiptCancelRequest,
    GoodsReceiptCreateRequest,
    GoodsReceiptItemResponse,
    GoodsReceiptListResponse,
    GoodsReceiptResponse,
    GoodsReceiptUpdateRequest,
    InventoryItemResponse,
    InventoryListResponse,
    LowStockItem,
    LowStockResponse,
    LowStockSummary,
    MessageResponse,
    Pagination,
    StockMovementResponse,
    StockMovementsResponse,
)
from backend.modules.product.models import Product


def _to_brief(r) -> GoodsReceiptBriefResponse:
    return GoodsReceiptBriefResponse(
        id=r.id, code=r.code, supplier_id=r.supplier_id, supplier_name=None,
        total=r.total, paid_amount=r.paid_amount, status=r.status,
        completed_at=r.completed_at, created_at=r.created_at,
    )


async def _enrich_receipt(
    db: AsyncSession, tenant_id: int, receipt
) -> GoodsReceiptResponse:
    supplier_name = None
    if receipt.supplier_id:
        s = await db.get(Supplier, receipt.supplier_id)
        supplier_name = s.name if s else None

    # Fetch products for items
    product_ids = [it.product_id for it in receipt.items]
    products = {}
    if product_ids:
        rows = (
            await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )
        ).scalars().all()
        products = {p.id: p for p in rows}

    item_responses = []
    for it in receipt.items:
        p = products.get(it.product_id)
        item_responses.append(
            GoodsReceiptItemResponse(
                id=it.id,
                product_id=it.product_id,
                product_name=p.name if p else None,
                product_sku=p.sku if p else None,
                quantity=it.quantity,
                cost_price=it.cost_price,
                line_total=it.line_total,
            )
        )

    return GoodsReceiptResponse(
        id=receipt.id,
        code=receipt.code,
        supplier_id=receipt.supplier_id,
        supplier_name=supplier_name,
        total=receipt.total,
        paid_amount=receipt.paid_amount,
        status=receipt.status,
        note=receipt.note,
        completed_at=receipt.completed_at,
        created_at=receipt.created_at,
        items=item_responses,
    )


# ====================================================================
# GOODS RECEIPTS
# ====================================================================

receipt_router = APIRouter(
    prefix="/api/v1/goods-receipts", tags=["goods-receipts"]
)


@receipt_router.get("", response_model=GoodsReceiptListResponse)
async def list_receipts(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(default=None),
    supplier_id: int | None = Query(default=None, ge=1),
):
    result = await inv_service.list_goods_receipts(
        db,
        tenant_id=user.current_tenant_id,
        page=page,
        limit=limit,
        status=status,
        supplier_id=supplier_id,
    )
    return GoodsReceiptListResponse(
        items=[_to_brief(r) for r in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@receipt_router.get("/{receipt_id}", response_model=GoodsReceiptResponse)
async def get_receipt(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    receipt_id: int = Path(..., ge=1),
):
    receipt = await inv_service.get_receipt(
        db, user.current_tenant_id, receipt_id
    )
    return await _enrich_receipt(db, user.current_tenant_id, receipt)


@receipt_router.post(
    "", response_model=GoodsReceiptResponse, status_code=status.HTTP_201_CREATED
)
async def create_receipt(
    payload: GoodsReceiptCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    receipt = await inv_service.create_goods_receipt(
        db, user.current_tenant_id, user.id, payload
    )
    return await _enrich_receipt(db, user.current_tenant_id, receipt)


@receipt_router.put("/{receipt_id}", response_model=GoodsReceiptResponse)
async def update_receipt(
    payload: GoodsReceiptUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    receipt_id: int = Path(..., ge=1),
):
    receipt = await inv_service.update_goods_receipt(
        db, user.current_tenant_id, user.id, receipt_id, payload
    )
    return await _enrich_receipt(db, user.current_tenant_id, receipt)


@receipt_router.post(
    "/{receipt_id}/complete", response_model=GoodsReceiptResponse
)
async def complete_receipt(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    receipt_id: int = Path(..., ge=1),
):
    receipt = await inv_service.complete_goods_receipt(
        db, user.current_tenant_id, receipt_id, user.id
    )
    return await _enrich_receipt(db, user.current_tenant_id, receipt)


@receipt_router.post(
    "/{receipt_id}/cancel", response_model=GoodsReceiptResponse
)
async def cancel_receipt(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    payload: GoodsReceiptCancelRequest = GoodsReceiptCancelRequest(),
    receipt_id: int = Path(..., ge=1),
):
    receipt = await inv_service.cancel_goods_receipt(
        db, user.current_tenant_id, receipt_id, user.id, payload.reason
    )
    return await _enrich_receipt(db, user.current_tenant_id, receipt)


# ====================================================================
# INVENTORY
# ====================================================================

inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@inventory_router.get("", response_model=InventoryListResponse)
async def list_inventory(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    only_with_stock: bool = Query(default=False),
):
    result = await inv_service.list_inventory(
        db,
        tenant_id=user.current_tenant_id,
        page=page,
        limit=limit,
        search=search,
        only_with_stock=only_with_stock,
    )
    return InventoryListResponse(
        items=[InventoryItemResponse(**i) for i in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@inventory_router.get("/low-stock", response_model=LowStockResponse)
async def low_stock(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    """Cảnh báo hàng sắp/hết — OWNER-only.

    CASHIER không được xem để tránh phân tâm trong ca bán; chủ shop là người
    chịu trách nhiệm đặt hàng và quyết định nhập kho.
    """
    data = await inv_service.list_low_stock(db, owner.current_tenant_id)
    return LowStockResponse(
        items=[LowStockItem(**i) for i in data["items"]],
        summary=LowStockSummary(**data["summary"]),
    )


@inventory_router.post(
    "/adjustments",
    response_model=AdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_adjustment(
    payload: AdjustmentCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    results = await inv_service.create_stock_adjustment(
        db, owner.current_tenant_id, owner.id, payload
    )
    return AdjustmentResponse(
        items=[AdjustmentResultItem(**r) for r in results]
    )


@inventory_router.get(
    "/adjustments", response_model=AdjustmentMovementsResponse
)
async def list_adjustments(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    result = await inv_service.list_adjustments(
        db, user.current_tenant_id, page=page, limit=limit
    )
    return AdjustmentMovementsResponse(
        items=[AdjustmentMovementResponse(**i) for i in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@inventory_router.get(
    "/{product_id}/movements", response_model=StockMovementsResponse
)
async def list_movements(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    result = await inv_service.list_movements(
        db, user.current_tenant_id, product_id, page=page, limit=limit
    )
    return StockMovementsResponse(
        items=[StockMovementResponse.model_validate(m) for m in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )
