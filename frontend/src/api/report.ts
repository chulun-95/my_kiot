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
