from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_role
from backend.modules.auth.models import User
from backend.modules.sales import return_service
from backend.modules.sales.return_schemas import (
    Pagination,
    ReturnCancelRequest,
    ReturnCreateRequest,
    ReturnListItem,
    ReturnListResponse,
    ReturnResponse,
    ReturnableInvoiceResponse,
)

router = APIRouter(prefix="/api/v1/returns", tags=["returns"])


@router.get("", response_model=ReturnListResponse)
async def list_returns(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    data = await return_service.list_returns(db, user.current_tenant_id, page=page, limit=limit)
    return ReturnListResponse(
        items=[ReturnListItem.model_validate(i) for i in data["items"]],
        pagination=Pagination(**data["pagination"]),
    )


@router.get("/returnable/{invoice_id}", response_model=ReturnableInvoiceResponse)
async def returnable(
    invoice_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    data = await return_service.get_returnable(db, user.current_tenant_id, invoice_id)
    return ReturnableInvoiceResponse(**data)


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return(
    return_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ro = await return_service.get_return(db, user.current_tenant_id, return_id)
    return ReturnResponse.model_validate(ro)


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: ReturnCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ro = await return_service.create_return(db, user.current_tenant_id, user.id, payload)
    return ReturnResponse.model_validate(ro)


@router.post("/{return_id}/cancel", response_model=ReturnResponse)
async def cancel_return(
    return_id: int,
    payload: ReturnCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    ro = await return_service.cancel_return(db, owner.current_tenant_id, owner.id, return_id, payload.reason)
    return ReturnResponse.model_validate(ro)
