from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProductStatus = Literal["ACTIVE", "INACTIVE", "DRAFT"]


# ---------- Category ----------

class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: int | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None
    depth: int
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryNode(BaseModel):
    id: int
    name: str
    depth: int
    sort_order: int
    children: list["CategoryNode"] = []


class CategoryTreeResponse(BaseModel):
    items: list[CategoryNode]


# ---------- Product ----------

class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    sku: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=50)
    category_id: int | None = None
    description: str | None = None
    unit: str = Field(default="cái", max_length=30)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    min_stock: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    status: ProductStatus = "ACTIVE"
    allow_negative: bool = False

    @field_validator("sku", "barcode")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    sku: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=50)
    category_id: int | None = None
    description: str | None = None
    unit: str | None = Field(default=None, max_length=30)
    cost_price: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    status: ProductStatus | None = None
    allow_negative: bool | None = None

    @field_validator("sku", "barcode")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductUnitResponse(BaseModel):
    id: int
    unit_name: str
    conversion_rate: Decimal
    sale_price: Decimal | None
    barcode: str | None

    model_config = ConfigDict(from_attributes=True)


class ProductUnitCreateRequest(BaseModel):
    unit_name: str = Field(min_length=1, max_length=30)
    conversion_rate: Decimal = Field(gt=1)
    sale_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=50)

    @field_validator("barcode")
    @classmethod
    def _strip_barcode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductUnitUpdateRequest(BaseModel):
    unit_name: str | None = Field(default=None, min_length=1, max_length=30)
    conversion_rate: Decimal | None = Field(default=None, gt=1)
    sale_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=50)

    @field_validator("barcode")
    @classmethod
    def _strip_barcode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductResponse(BaseModel):
    id: int
    sku: str
    barcode: str | None
    name: str
    description: str | None
    unit: str
    cost_price: Decimal | None = None
    sale_price: Decimal
    min_stock: int
    image_url: str | None
    status: ProductStatus
    allow_negative: bool
    category_id: int | None
    category_name: str | None = None
    created_at: datetime
    updated_at: datetime
    units: list[ProductUnitResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProductBriefResponse(BaseModel):
    """Dùng cho search/barcode lookup ở POS — payload nhẹ.
    cost_price=None khi CASHIER không có quyền xem giá vốn.
    """

    id: int
    sku: str
    barcode: str | None
    name: str
    unit: str
    sale_price: Decimal
    cost_price: Decimal | None = None
    image_url: str | None
    allow_negative: bool
    status: ProductStatus
    units: list[ProductUnitResponse] = []
    matched_unit: ProductUnitResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    pagination: Pagination


class ProductSearchResponse(BaseModel):
    items: list[ProductBriefResponse]


class MessageResponse(BaseModel):
    message: str


CategoryNode.model_rebuild()
