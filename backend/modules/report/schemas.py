from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


RevenueGroupBy = Literal["day", "month"]


# ---------- Dashboard ----------

class DashboardResponse(BaseModel):
    today_revenue: Decimal
    today_invoices: int
    today_profit: Decimal | None = None   # None nếu CASHIER không được xem lợi nhuận
    today_customers: int
    pending_drafts: int
    low_stock_count: int       # gồm cả OUT_OF_STOCK + LOW
    out_of_stock_count: int    # subset của low_stock_count: tồn ≤ 0
    inventory_value: Decimal | None = None  # None nếu CASHIER không được xem giá vốn


class HubSummaryResponse(BaseModel):
    total_products: int
    low_stock_count: int       # gồm cả OUT_OF_STOCK + LOW (giống dashboard)
    out_of_stock_count: int    # subset của low_stock_count: tồn ≤ 0
    total_customers: int
    total_suppliers: int
    draft_receipts_count: int


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


# ---------- Products Sold (báo cáo SP đã bán) ----------

ProductsSoldSortBy = Literal["revenue", "quantity", "profit"]
SortOrder = Literal["asc", "desc"]


class ProductsSoldItem(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    quantity_sold: Decimal      # đơn vị cơ bản
    revenue: Decimal            # doanh thu gộp (trước giảm giá)
    discount: Decimal
    net_revenue: Decimal        # doanh thu thuần
    cost: Decimal               # giá vốn
    profit: Decimal             # lợi nhuận gộp
    margin_pct: Decimal         # tỷ suất % (= profit / net_revenue * 100)


class ProductsSoldTotals(BaseModel):
    quantity_sold: Decimal
    revenue: Decimal
    discount: Decimal
    net_revenue: Decimal
    cost: Decimal
    profit: Decimal


class ProductsSoldPagination(BaseModel):
    page: int
    limit: int
    total: int           # tổng số SP (distinct) khớp bộ lọc
    total_pages: int


class ProductsSoldResponse(BaseModel):
    from_date: date
    to_date: date
    sort_by: ProductsSoldSortBy
    order: SortOrder
    category_id: int | None
    items: list[ProductsSoldItem]
    totals: ProductsSoldTotals
    pagination: ProductsSoldPagination


# ---------- Debt Report ----------

class DebtItem(BaseModel):
    partner_id: int
    partner_name: str
    phone: str | None = None
    debt: Decimal


class DebtReportResponse(BaseModel):
    items: list[DebtItem]
    total_debt: Decimal


# ---------- End-of-Day ----------

class EodMethodRow(BaseModel):
    method: str
    opening: Decimal
    total_in: Decimal
    total_out: Decimal
    closing: Decimal


class EndOfDayResponse(BaseModel):
    business_date: date
    by_method: list[EodMethodRow]
    opening_total: Decimal
    in_total: Decimal
    out_total: Decimal
    closing_total: Decimal
    sales_revenue: Decimal      # doanh thu hóa đơn trong ngày, đã trừ trả hàng
    sales_invoices: int
