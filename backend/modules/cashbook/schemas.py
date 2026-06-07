from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


CashDirection = Literal["IN", "OUT"]
CashMethod = Literal["CASH", "BANK_TRANSFER", "EWALLET"]
CashStatus = Literal["ACTIVE", "CANCELLED"]
# Category cho phép tạo TAY (auto-only SALE/PURCHASE/CHANGE bị loại)
ManualInCategory = Literal["OTHER_IN", "CAPITAL"]
ManualOutCategory = Literal["SALARY", "OPERATING", "OTHER_OUT"]


class CashTransactionCreate(BaseModel):
    direction: CashDirection
    method: CashMethod = "CASH"
    category: str = Field(min_length=1, max_length=20)
    amount: Decimal = Field(gt=0)
    partner_type: Optional[Literal["CUSTOMER", "SUPPLIER", "OTHER"]] = None
    partner_id: Optional[int] = None
    partner_name: Optional[str] = Field(default=None, max_length=200)
    note: Optional[str] = None


class CashTransactionResponse(BaseModel):
    id: int
    code: str
    direction: CashDirection
    method: CashMethod
    category: str
    amount: Decimal
    ref_type: str
    ref_id: Optional[int]
    partner_type: Optional[str]
    partner_id: Optional[int]
    partner_name: Optional[str]
    note: Optional[str]
    status: CashStatus
    created_at: datetime
    created_by: Optional[int]

    class Config:
        from_attributes = True


class CashCancelRequest(BaseModel):
    reason: Optional[str] = None


class CashPagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class MethodBalance(BaseModel):
    method: CashMethod
    balance: Decimal


class CashSummary(BaseModel):
    range_in: Decimal       # tổng thu trong kỳ lọc
    range_out: Decimal      # tổng chi trong kỳ lọc
    balance_total: Decimal  # tồn quỹ hiện tại (toàn bộ ACTIVE, mọi phương thức)
    balance_by_method: list[MethodBalance]


class CashListResponse(BaseModel):
    items: list[CashTransactionResponse]
    summary: CashSummary
    pagination: CashPagination
