from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------- Customer ----------

class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    note: str | None = None

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    note: str | None = None

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    address: str | None
    note: str | None
    total_spent: Decimal
    total_orders: int
    last_order_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerBrief(BaseModel):
    """Cho POS — payload nhẹ."""

    id: int
    name: str
    phone: str | None
    total_spent: Decimal
    total_orders: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Supplier ----------

class SupplierCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    tax_code: str | None = Field(default=None, max_length=20)
    note: str | None = None


class SupplierUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    tax_code: str | None = Field(default=None, max_length=20)
    note: str | None = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    address: str | None
    tax_code: str | None
    note: str | None
    total_debt: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- pagination + invoice history ----------

class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    pagination: Pagination


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    pagination: Pagination


class CustomerOrderHistoryItem(BaseModel):
    invoice_id: int
    code: str
    total: Decimal
    completed_at: datetime | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CustomerDetailResponse(BaseModel):
    customer: CustomerResponse
    recent_orders: list[CustomerOrderHistoryItem] = []


class MessageResponse(BaseModel):
    message: str
