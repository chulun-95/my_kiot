from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InvoiceStatus = Literal["DRAFT", "COMPLETED", "CANCELLED"]
PaymentMethod = Literal["CASH", "BANK_TRANSFER", "MOMO", "VNPAY", "OTHER"]


# ---------- request ----------

class InvoiceItemInput(BaseModel):
    product_id: int = Field(ge=1)
    unit_id: int | None = None
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)


class InvoiceCreateRequest(BaseModel):
    customer_id: int | None = None
    items: list[InvoiceItemInput] = Field(default_factory=list)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = None


class InvoiceUpdateRequest(BaseModel):
    customer_id: int | None = None
    items: list[InvoiceItemInput] | None = None
    discount_amount: Decimal | None = Field(default=None, ge=0)
    note: str | None = None


class PaymentInput(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    note: str | None = None


class InvoiceCompleteRequest(BaseModel):
    payments: list[PaymentInput] = Field(default_factory=list)
    allow_debt: bool = False  # cho phép thiếu nợ


class InvoiceCancelRequest(BaseModel):
    reason: str | None = None


# ---------- response ----------

class InvoiceItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    unit: str | None
    unit_id: int | None = None
    conversion_rate: Decimal | None = None
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal
    discount_amount: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(BaseModel):
    id: int
    method: str
    amount: Decimal
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    id: int
    code: str
    customer_id: int | None
    customer_name: str | None = None
    cashier_id: int
    cashier_name: str | None = None
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    cost_total: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    status: InvoiceStatus
    note: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    items: list[InvoiceItemResponse]
    payments: list[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class InvoiceBriefResponse(BaseModel):
    id: int
    code: str
    customer_id: int | None
    customer_name: str | None = None
    cashier_id: int
    total: Decimal
    paid_amount: Decimal
    status: InvoiceStatus
    completed_at: datetime | None
    created_at: datetime


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class InvoiceListResponse(BaseModel):
    items: list[InvoiceBriefResponse]
    pagination: Pagination


class InvoiceDraftListResponse(BaseModel):
    items: list[InvoiceBriefResponse]


class MessageResponse(BaseModel):
    message: str
