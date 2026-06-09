from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RefundMethod = Literal["CASH", "BANK_TRANSFER", "EWALLET"]


class ReturnItemInput(BaseModel):
    invoice_item_id: int
    quantity: Decimal = Field(gt=0)


class ReturnCreateRequest(BaseModel):
    invoice_id: int
    items: list[ReturnItemInput] = Field(min_length=1)
    refund_method: RefundMethod = "CASH"
    reason: Optional[str] = None


class ReturnCancelRequest(BaseModel):
    reason: Optional[str] = None


class ReturnItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class ReturnResponse(BaseModel):
    id: int
    code: str
    invoice_id: int
    customer_id: Optional[int]
    customer_name: Optional[str]
    total_refund: Decimal
    debt_adjust: Decimal
    cash_refund: Decimal
    refund_method: str
    status: str
    reason: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    items: list[ReturnItemResponse]
    model_config = ConfigDict(from_attributes=True)


class ReturnListItem(BaseModel):
    id: int
    code: str
    invoice_id: int
    customer_name: Optional[str]
    total_refund: Decimal
    refund_method: str
    status: str
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ReturnListResponse(BaseModel):
    items: list[ReturnListItem]
    pagination: Pagination


# Số đã trả còn lại theo từng dòng hóa đơn (cho FE dựng form)
class ReturnableLine(BaseModel):
    invoice_item_id: int
    product_id: int
    product_name: str
    product_sku: str
    unit: Optional[str]
    sold_quantity: Decimal
    returned_quantity: Decimal
    returnable_quantity: Decimal
    unit_price: Decimal


class ReturnableInvoiceResponse(BaseModel):
    invoice_id: int
    invoice_code: str
    customer_id: Optional[int]
    customer_name: Optional[str]
    lines: list[ReturnableLine]
