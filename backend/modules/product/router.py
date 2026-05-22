from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_role
from backend.modules.auth.models import User
from backend.modules.product import service as product_service
from backend.shared.settings import can_see_cost
from backend.modules.product.schemas import (
    CategoryCreateRequest,
    CategoryNode,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
    MessageResponse,
    Pagination,
    ProductBriefResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductSearchResponse,
    ProductUpdateRequest,
    ProductUnitCreateRequest,
    ProductUnitResponse,
    ProductUnitUpdateRequest,
)


# ====================================================================
# CATEGORIES
# ====================================================================

category_router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


def _to_category_response(c) -> CategoryResponse:
    return CategoryResponse.model_validate(c)


def _node_from_dict(d: dict) -> CategoryNode:
    return CategoryNode(
        id=d["id"],
        name=d["name"],
        depth=d["depth"],
        sort_order=d["sort_order"],
        children=[_node_from_dict(c) for c in d["children"]],
    )


@category_router.get("", response_model=CategoryTreeResponse)
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    tree = await product_service.list_categories_tree(db, user.current_tenant_id)
    return CategoryTreeResponse(items=[_node_from_dict(d) for d in tree])


@category_router.post(
    "", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    payload: CategoryCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    cat = await product_service.create_category(
        db, user.current_tenant_id, user.id, payload
    )
    return _to_category_response(cat)


@category_router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    payload: CategoryUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    category_id: int = Path(..., ge=1),
):
    cat = await product_service.update_category(
        db, user.current_tenant_id, user.id, category_id, payload
    )
    return _to_category_response(cat)


@category_router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    category_id: int = Path(..., ge=1),
):
    await product_service.delete_category(
        db, user.current_tenant_id, user.id, category_id
    )
    return MessageResponse(message="Đã xóa nhóm hàng")


# ====================================================================
# PRODUCTS
# ====================================================================

product_router = APIRouter(prefix="/api/v1/products", tags=["products"])


def _to_product_response(p, user: User) -> ProductResponse:
    show_cost = can_see_cost(getattr(user, "_tenant", None), user.role)
    data = {
        "id": p.id,
        "sku": p.sku,
        "barcode": p.barcode,
        "name": p.name,
        "description": p.description,
        "unit": p.unit,
        "cost_price": p.cost_price if show_cost else None,
        "sale_price": p.sale_price,
        "min_stock": p.min_stock,
        "image_url": p.image_url,
        "status": p.status,
        "allow_negative": p.allow_negative,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "units": [ProductUnitResponse.model_validate(u) for u in (p.units or [])],
    }
    return ProductResponse(**data)


def _to_brief_response(p, user: User, matched_unit=None) -> ProductBriefResponse:
    show_cost = can_see_cost(getattr(user, "_tenant", None), user.role)
    return ProductBriefResponse(
        id=p.id,
        sku=p.sku,
        barcode=p.barcode,
        name=p.name,
        unit=p.unit,
        sale_price=p.sale_price,
        cost_price=p.cost_price if show_cost else None,
        image_url=p.image_url,
        allow_negative=p.allow_negative,
        status=p.status,
        units=[ProductUnitResponse.model_validate(u) for u in (p.units or [])],
        matched_unit=ProductUnitResponse.model_validate(matched_unit) if matched_unit else None,
    )


@product_router.get("", response_model=ProductListResponse)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
):
    result = await product_service.list_products(
        db,
        tenant_id=user.current_tenant_id,
        page=page,
        limit=limit,
        search=search,
        category_id=category_id,
        status=status,
    )
    return ProductListResponse(
        items=[_to_product_response(p, user) for p in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@product_router.get("/search", response_model=ProductSearchResponse)
async def search_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
):
    products = await product_service.search_products(
        db, user.current_tenant_id, query=q, limit=limit
    )
    return ProductSearchResponse(
        items=[_to_brief_response(p, user) for p in products]
    )


@product_router.get("/barcode/{code}", response_model=ProductBriefResponse)
async def get_by_barcode(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    code: str = Path(..., min_length=1, max_length=50),
):
    product, matched_unit = await product_service.get_by_barcode(
        db, user.current_tenant_id, code
    )
    return _to_brief_response(product, user, matched_unit=matched_unit)


@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    product = await product_service.get_product(
        db, user.current_tenant_id, product_id
    )
    return _to_product_response(product, user)


@product_router.post(
    "", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
async def create_product(
    payload: ProductCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    product = await product_service.create_product(
        db, user.current_tenant_id, user.id, payload
    )
    product = await product_service.get_product(
        db, user.current_tenant_id, product.id
    )
    return _to_product_response(product, user)


@product_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    payload: ProductUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    product = await product_service.update_product(
        db, user.current_tenant_id, user.id, product_id, payload
    )
    product = await product_service.get_product(
        db, user.current_tenant_id, product.id
    )
    return _to_product_response(product, user)


@product_router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    await product_service.soft_delete_product(
        db, user.current_tenant_id, user.id, product_id
    )
    return MessageResponse(message="Đã ngừng bán sản phẩm")


# ====================================================================
# PRODUCT UNITS
# ====================================================================

@product_router.get("/{product_id}/units", response_model=list[ProductUnitResponse])
async def list_units(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    return await product_service.list_product_units(db, user.current_tenant_id, product_id)


@product_router.post(
    "/{product_id}/units",
    response_model=ProductUnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("OWNER"))],
)
async def create_unit(
    payload: ProductUnitCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    return await product_service.create_product_unit(
        db, user.current_tenant_id, user.id, product_id, payload
    )


@product_router.put(
    "/{product_id}/units/{unit_id}",
    response_model=ProductUnitResponse,
    dependencies=[Depends(require_role("OWNER"))],
)
async def update_unit(
    payload: ProductUnitUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
    unit_id: int = Path(..., ge=1),
):
    return await product_service.update_product_unit(
        db, user.current_tenant_id, user.id, product_id, unit_id, payload
    )


@product_router.delete(
    "/{product_id}/units/{unit_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("OWNER"))],
)
async def delete_unit(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
    unit_id: int = Path(..., ge=1),
):
    await product_service.delete_product_unit(
        db, user.current_tenant_id, user.id, product_id, unit_id
    )
    return MessageResponse(message="Xóa đơn vị thành công")
