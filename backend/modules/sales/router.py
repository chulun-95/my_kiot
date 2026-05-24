from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_role
from backend.exceptions import AppError
from backend.modules.auth.models import User
from backend.modules.customer.models import Customer
from backend.modules.sales import service as sales_service
from backend.modules.sales.models import Invoice
from backend.modules.sales.schemas import (
    InvoiceBriefResponse,
    InvoiceCancelRequest,
    InvoiceCompleteRequest,
    InvoiceCreateRequest,
    InvoiceDraftListResponse,
    InvoiceItemResponse,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdateRequest,
    MessageResponse,
    Pagination,
    PaymentResponse,
)


def _to_invoice_response(
    inv: Invoice,
    customer_name: str | None = None,
    cashier_name: str | None = None,
) -> InvoiceResponse:
    return InvoiceResponse(
        id=inv.id,
        code=inv.code,
        customer_id=inv.customer_id,
        customer_name=customer_name,
        cashier_id=inv.cashier_id,
        cashier_name=cashier_name,
        subtotal=inv.subtotal,
        discount_amount=inv.discount_amount,
        total=inv.total,
        cost_total=inv.cost_total,
        paid_amount=inv.paid_amount,
        change_amount=inv.change_amount,
        status=inv.status,
        note=inv.note,
        completed_at=inv.completed_at,
        cancelled_at=inv.cancelled_at,
        cancel_reason=inv.cancel_reason,
        created_at=inv.created_at,
        items=[InvoiceItemResponse.model_validate(it) for it in inv.items],
        payments=[PaymentResponse.model_validate(p) for p in inv.payments],
    )


def _to_brief(inv: Invoice, customer_name: str | None = None) -> InvoiceBriefResponse:
    return InvoiceBriefResponse(
        id=inv.id,
        code=inv.code,
        customer_id=inv.customer_id,
        customer_name=customer_name,
        cashier_id=inv.cashier_id,
        total=inv.total,
        paid_amount=inv.paid_amount,
        status=inv.status,
        completed_at=inv.completed_at,
        created_at=inv.created_at,
    )


async def _enrich_invoice(
    db: AsyncSession, tenant_id: int, inv: Invoice
) -> InvoiceResponse:
    customer_name = None
    if inv.customer_id:
        c = await db.get(Customer, inv.customer_id)
        customer_name = c.name if c else None
    cashier_name = None
    if inv.cashier_id:
        u = await db.get(User, inv.cashier_id)
        cashier_name = u.full_name if u else None
    return _to_invoice_response(inv, customer_name, cashier_name)


router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None, ge=1),
    cashier_id: int | None = Query(default=None, ge=1),
):
    result = await sales_service.list_invoices(
        db,
        tenant_id=user.current_tenant_id,
        page=page,
        limit=limit,
        status=status_filter,
        customer_id=customer_id,
        cashier_id=cashier_id,
    )
    return InvoiceListResponse(
        items=[_to_brief(inv) for inv in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@router.get("/drafts", response_model=InvoiceDraftListResponse)
async def list_drafts(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    mine_only: bool = Query(default=True),
):
    cashier_id = user.id if (user.role == "CASHIER" or mine_only) else None
    drafts = await sales_service.list_drafts(
        db, user.current_tenant_id, cashier_id=cashier_id
    )
    return InvoiceDraftListResponse(items=[_to_brief(inv) for inv in drafts])


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    invoice_id: int = Path(..., ge=1),
):
    invoice = await sales_service.get_invoice(
        db, user.current_tenant_id, invoice_id
    )
    return await _enrich_invoice(db, user.current_tenant_id, invoice)


@router.post(
    "", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED
)
async def create_invoice(
    payload: InvoiceCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    invoice = await sales_service.create_invoice(
        db, user.current_tenant_id, user.id, payload
    )
    return await _enrich_invoice(db, user.current_tenant_id, invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    payload: InvoiceUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    invoice_id: int = Path(..., ge=1),
):
    invoice = await sales_service.update_invoice(
        db, user.current_tenant_id, user.id, invoice_id, payload
    )
    return await _enrich_invoice(db, user.current_tenant_id, invoice)


@router.post("/{invoice_id}/complete", response_model=InvoiceResponse)
async def complete_invoice(
    payload: InvoiceCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    invoice_id: int = Path(..., ge=1),
):
    invoice = await sales_service.complete_invoice(
        db, user.current_tenant_id, invoice_id, user.id, payload
    )
    return await _enrich_invoice(db, user.current_tenant_id, invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    payload: InvoiceCancelRequest = InvoiceCancelRequest(),
    invoice_id: int = Path(..., ge=1),
):
    # Permission rule:
    # - CASHIER: chỉ được hủy DRAFT của chính mình
    # - OWNER: hủy DRAFT hoặc COMPLETED của bất kỳ ai
    invoice = await sales_service.get_invoice(
        db, user.current_tenant_id, invoice_id
    )
    if user.role != "OWNER":
        if invoice.status == "COMPLETED":
            raise AppError(
                403,
                "FORBIDDEN_CANCEL_COMPLETED",
                "Chỉ OWNER mới được hủy hóa đơn đã hoàn tất",
            )
        if invoice.status == "DRAFT" and invoice.cashier_id != user.id:
            raise AppError(
                403,
                "FORBIDDEN_CANCEL_OTHERS_DRAFT",
                "Chỉ OWNER mới được hủy nháp của người khác",
            )

    invoice = await sales_service.cancel_invoice(
        db, user.current_tenant_id, invoice_id, user.id, payload.reason
    )
    return await _enrich_invoice(db, user.current_tenant_id, invoice)
