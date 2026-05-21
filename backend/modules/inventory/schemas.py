from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReceiptStatus = Literal["DRAFT", "COMPLETED", "CANCELLED"]


# ---------- Goods Receipt ----------

class GoodsReceiptItemInput(BaseModel):
    product_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)

    @field_validator("quantity", "cost_price")
    @classmethod
    def _positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class GoodsReceiptCreateRequest(BaseModel):
    supplier_id: int | None = None
    items: list[GoodsReceiptItemInput] = Field(min_length=1)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = None


class GoodsReceiptUpdateRequest(BaseModel):
    """Chỉ sửa được phiếu DRAFT."""

    supplier_id: int | None = None
    items: list[GoodsReceiptItemInput] | None = None
    paid_amount: Decimal | None = Field(default=None, ge=0)
    note: str | None = None


class GoodsReceiptItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    product_sku: str | None = None
    quantity: Decimal
    cost_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptResponse(BaseModel):
    id: int
    code: str
    supplier_id: int | None
    supplier_name: str | None = None
    total: Decimal
    paid_amount: Decimal
    status: ReceiptStatus
    note: str | None
    completed_at: datetime | None
    created_at: datetime
    items: list[GoodsReceiptItemResponse]

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptBriefResponse(BaseModel):
    id: int
    code: str
    supplier_id: int | None
    supplier_name: str | None = None
    total: Decimal
    paid_amount: Decimal
    status: ReceiptStatus
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptCancelRequest(BaseModel):
    reason: str | None = None


# ---------- Inventory ----------

class InventoryItemResponse(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    unit: str
    quantity: Decimal
    min_stock: int
    cost_price: Decimal
    sale_price: Decimal


class StockMovementResponse(BaseModel):
    id: int
    quantity: Decimal
    unit_cost: Decimal | None
    type: str
    ref_type: str
    ref_id: int
    balance_after: Decimal
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class InventoryListResponse(BaseModel):
    items: list[InventoryItemResponse]
    pagination: Pagination


class StockMovementsResponse(BaseModel):
    items: list[StockMovementResponse]
    pagination: Pagination


class GoodsReceiptListResponse(BaseModel):
    items: list[GoodsReceiptBriefResponse]
    pagination: Pagination


class LowStockItem(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    unit: str
    quantity: Decimal
    min_stock: int


class LowStockResponse(BaseModel):
    items: list[LowStockItem]


# ---------- Stocktake / Adjustment ----------

class AdjustmentItemInput(BaseModel):
    product_id: int = Field(ge=1)
    new_quantity: Decimal = Field(ge=0)
    reason: str | None = None


class AdjustmentCreateRequest(BaseModel):
    items: list[AdjustmentItemInput] = Field(min_length=1)


class AdjustmentResultItem(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    old_quantity: Decimal
    new_quantity: Decimal
    delta: Decimal
    movement_id: int


class AdjustmentResponse(BaseModel):
    items: list[AdjustmentResultItem]


class AdjustmentMovementResponse(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    product_sku: str | None = None
    quantity: Decimal
    balance_after: Decimal
    note: str | None
    created_at: datetime
    created_by: int


class AdjustmentMovementsResponse(BaseModel):
    items: list[AdjustmentMovementResponse]
    pagination: Pagination


class MessageResponse(BaseModel):
    message: str
