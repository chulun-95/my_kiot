from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.modules.auth.models import User
from backend.modules.customer import service as customer_service
from backend.modules.customer.schemas import (
    CustomerCreateRequest,
    CustomerDetailResponse,
    CustomerListResponse,
    CustomerOrderHistoryItem,
    CustomerResponse,
    CustomerUpdateRequest,
    MessageResponse,
    Pagination,
    SupplierCreateRequest,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdateRequest,
)


# ====================================================================
# CUSTOMERS
# ====================================================================

customer_router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@customer_router.get("", response_model=CustomerListResponse)
async def list_customers(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    result = await customer_service.list_customers(
        db, user.current_tenant_id, page=page, limit=limit, search=search
    )
    return CustomerListResponse(
        items=[CustomerResponse.model_validate(c) for c in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@customer_router.get("/phone/{phone}", response_model=CustomerResponse)
async def find_by_phone(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    phone: str = Path(..., min_length=1, max_length=20),
):
    customer = await customer_service.find_by_phone(
        db, user.current_tenant_id, phone
    )
    return CustomerResponse.model_validate(customer)


@customer_router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    customer_id: int = Path(..., ge=1),
):
    customer = await customer_service.get_customer(
        db, user.current_tenant_id, customer_id
    )
    orders = await customer_service.get_recent_orders(
        db, user.current_tenant_id, customer_id, limit=10
    )
    return CustomerDetailResponse(
        customer=CustomerResponse.model_validate(customer),
        recent_orders=[CustomerOrderHistoryItem(**o) for o in orders],
    )


@customer_router.post(
    "", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED
)
async def create_customer(
    payload: CustomerCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    customer = await customer_service.create_customer(
        db, user.current_tenant_id, user.id, payload
    )
    return CustomerResponse.model_validate(customer)


@customer_router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    payload: CustomerUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    customer_id: int = Path(..., ge=1),
):
    customer = await customer_service.update_customer(
        db, user.current_tenant_id, user.id, customer_id, payload
    )
    return CustomerResponse.model_validate(customer)


@customer_router.delete("/{customer_id}", response_model=MessageResponse)
async def delete_customer(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    customer_id: int = Path(..., ge=1),
):
    await customer_service.soft_delete_customer(
        db, user.current_tenant_id, user.id, customer_id
    )
    return MessageResponse(message="Đã xóa khách hàng")


# ====================================================================
# SUPPLIERS
# ====================================================================

supplier_router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@supplier_router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    result = await customer_service.list_suppliers(
        db, user.current_tenant_id, page=page, limit=limit, search=search
    )
    return SupplierListResponse(
        items=[SupplierResponse.model_validate(s) for s in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@supplier_router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    supplier_id: int = Path(..., ge=1),
):
    s = await customer_service.get_supplier(
        db, user.current_tenant_id, supplier_id
    )
    return SupplierResponse.model_validate(s)


@supplier_router.post(
    "", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED
)
async def create_supplier(
    payload: SupplierCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    s = await customer_service.create_supplier(
        db, user.current_tenant_id, user.id, payload
    )
    return SupplierResponse.model_validate(s)


@supplier_router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    payload: SupplierUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    supplier_id: int = Path(..., ge=1),
):
    s = await customer_service.update_supplier(
        db, user.current_tenant_id, user.id, supplier_id, payload
    )
    return SupplierResponse.model_validate(s)


@supplier_router.delete("/{supplier_id}", response_model=MessageResponse)
async def delete_supplier(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    supplier_id: int = Path(..., ge=1),
):
    await customer_service.soft_delete_supplier(
        db, user.current_tenant_id, user.id, supplier_id
    )
    return MessageResponse(message="Đã xóa nhà cung cấp")
