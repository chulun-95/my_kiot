import apiClient from './client';

export interface DashboardResponse {
  today_revenue: number | string;
  today_invoices: number;
  today_profit: number | string;
  today_customers: number;
  pending_drafts: number;
  low_stock_count: number;
  out_of_stock_count: number;
  inventory_value: number | string;
}

export interface RevenuePoint {
  period: string;
  revenue: number | string;
  invoices: number;
  profit: number | string;
}

export type RevenueGroupBy = 'day' | 'month';

export interface RevenueResponse {
  from_date: string;
  to_date: string;
  group_by: RevenueGroupBy;
  total_revenue: number | string;
  total_profit: number | string;
  total_invoices: number;
  series: RevenuePoint[];
}

export interface TopProductItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_sold: number | string;
  revenue: number | string;
  profit: number | string;
}

export interface TopProductsResponse {
  from_date: string;
  to_date: string;
  items: TopProductItem[];
}

export type ProductsSoldSortBy = 'revenue' | 'quantity' | 'profit';
export type SortOrder = 'asc' | 'desc';

export interface ProductsSoldItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_sold: number | string;
  revenue: number | string;
  discount: number | string;
  net_revenue: number | string;
  cost: number | string;
  profit: number | string;
  margin_pct: number | string;
}

export interface ProductsSoldTotals {
  quantity_sold: number | string;
  revenue: number | string;
  discount: number | string;
  net_revenue: number | string;
  cost: number | string;
  profit: number | string;
}

export interface ProductsSoldPagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface ProductsSoldResponse {
  from_date: string;
  to_date: string;
  sort_by: ProductsSoldSortBy;
  order: SortOrder;
  category_id: number | null;
  items: ProductsSoldItem[];
  totals: ProductsSoldTotals;
  pagination: ProductsSoldPagination;
}

export interface ProductsSoldParams {
  from: string;
  to: string;
  category_id?: number;
  sort_by?: ProductsSoldSortBy;
  order?: SortOrder;
  page?: number;
  limit?: number;
}

export interface ProfitResponse {
  from_date: string;
  to_date: string;
  total_revenue: number | string;
  total_cost: number | string;
  gross_profit: number | string;
  invoices: number;
}

export interface StockSummaryResponse {
  total_products: number;
  products_in_stock: number;
  products_out_of_stock: number;
  low_stock_count: number;
  total_inventory_value: number | string;
  last_updated: string;
}

export interface DateRangeParams {
  from: string;
  to: string;
}

export async function getDashboard(): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>('/reports/dashboard');
  return data;
}

export async function getRevenue(
  params: DateRangeParams & { group_by: RevenueGroupBy },
): Promise<RevenueResponse> {
  const { data } = await apiClient.get<RevenueResponse>('/reports/revenue', {
    params,
  });
  return data;
}

export async function getTopProducts(
  params: DateRangeParams & { limit?: number },
): Promise<TopProductsResponse> {
  const { data } = await apiClient.get<TopProductsResponse>(
    '/reports/top-products',
    { params },
  );
  return data;
}

export async function getProductsSold(
  params: ProductsSoldParams,
): Promise<ProductsSoldResponse> {
  const { data } = await apiClient.get<ProductsSoldResponse>(
    '/reports/products-sold',
    { params },
  );
  return data;
}

export async function getProfit(
  params: DateRangeParams,
): Promise<ProfitResponse> {
  const { data } = await apiClient.get<ProfitResponse>('/reports/profit', {
    params,
  });
  return data;
}

export async function getStockSummary(): Promise<StockSummaryResponse> {
  const { data } = await apiClient.get<StockSummaryResponse>(
    '/reports/stock-summary',
  );
  return data;
}

export interface DebtItem {
  partner_id: number;
  partner_name: string;
  phone: string | null;
  debt: number | string;
}

export interface DebtReportResponse {
  items: DebtItem[];
  total_debt: number | string;
}

export async function getCustomerDebts(): Promise<DebtReportResponse> {
  const { data } = await apiClient.get<DebtReportResponse>('/reports/debts/customers');
  return data;
}

export async function getSupplierDebts(): Promise<DebtReportResponse> {
  const { data } = await apiClient.get<DebtReportResponse>('/reports/debts/suppliers');
  return data;
}

export interface EodMethodRow {
  method: string;
  opening: number | string;
  total_in: number | string;
  total_out: number | string;
  closing: number | string;
}

export interface EndOfDayResponse {
  business_date: string;
  by_method: EodMethodRow[];
  opening_total: number | string;
  in_total: number | string;
  out_total: number | string;
  closing_total: number | string;
  sales_revenue: number | string;
  sales_invoices: number;
}

export async function getEndOfDay(date?: string): Promise<EndOfDayResponse> {
  const { data } = await apiClient.get<EndOfDayResponse>('/reports/end-of-day', {
    params: date ? { date } : {},
  });
  return data;
}
