from __future__ import annotations
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_role
from backend.modules.auth.models import User
from backend.modules.cashbook import service as cash_service
from backend.modules.cashbook.schemas import (
    CashCancelRequest,
    CashListResponse,
    CashPagination,
    CashSummary,
    CashTransactionCreate,
    CashTransactionResponse,
)

router = APIRouter(prefix="/api/v1/cash-transactions", tags=["cashbook"])


@router.get("", response_model=CashListResponse)
async def list_cash(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    direction: Optional[str] = Query(default=None),
    method: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    ref_type: Optional[str] = Query(default=None),
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    data = await cash_service.list_cash_transactions(
        db, owner.current_tenant_id, direction=direction, method=method,
        category=category, ref_type=ref_type, from_date=from_date, to_date=to_date,
        page=page, limit=limit,
    )
    return CashListResponse(
        items=[CashTransactionResponse.model_validate(i) for i in data["items"]],
        summary=CashSummary(**data["summary"]),
        pagination=CashPagination(**data["pagination"]),
    )


@router.post("", response_model=CashTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_cash(
    payload: CashTransactionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    tx = await cash_service.create_cash_transaction(
        db, owner.current_tenant_id, owner.id, payload
    )
    return CashTransactionResponse.model_validate(tx)


@router.post("/{tx_id}/cancel", response_model=CashTransactionResponse)
async def cancel_cash(
    tx_id: int,
    payload: CashCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    tx = await cash_service.cancel_cash_transaction(
        db, owner.current_tenant_id, owner.id, tx_id, payload.reason
    )
    return CashTransactionResponse.model_validate(tx)
