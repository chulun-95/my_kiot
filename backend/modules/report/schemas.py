from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


RevenueGroupBy = Literal["day", "month"]


# ---------- Dashboard ----------

class DashboardResponse(BaseModel):
    today_revenue: Decimal
    today_invoices: int
    today_profit: Decimal
    today_customers: int
    pending_drafts: int
    low_stock_count: int
    inventory_value: Decimal  # tổng giá vốn tồn kho


# ---------- Revenue ----------

class RevenuePoint(BaseModel):
    period: str  # "2026-05-21" hoặc "2026-05"
    revenue: Decimal
    invoices: int
    profit: Decimal


class RevenueResponse(BaseModel):
    from_date: date
    to_date: date
    group_by: RevenueGroupBy
    total_revenue: Decimal
    total_profit: Decimal
    total_invoices: int
    series: list[RevenuePoint]


# ---------- Top Products ----------

class TopProductItem(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    quantity_sold: Decimal
    revenue: Decimal
    profit: Decimal


class TopProductsResponse(BaseModel):
    from_date: date
    to_date: date
    items: list[TopProductItem]


# ---------- Profit ----------

class ProfitResponse(BaseModel):
    from_date: date
    to_date: date
    total_revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    invoices: int


# ---------- Stock summary ----------

class StockSummaryResponse(BaseModel):
    total_products: int
    products_in_stock: int
    products_out_of_stock: int
    low_stock_count: int
    total_inventory_value: Decimal
    last_updated: datetime
