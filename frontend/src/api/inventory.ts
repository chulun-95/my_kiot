import apiClient from './client';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface InventoryItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  unit: string;
  quantity: number | string;
  min_stock: number;
  cost_price: number | string;
  sale_price: number | string;
}

export interface InventoryListResponse {
  items: InventoryItem[];
  pagination: Pagination;
}

export interface LowStockItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  unit: string;
  quantity: number | string;
  min_stock: number;
}

export interface LowStockResponse {
  items: LowStockItem[];
}

export type MovementType =
  | 'SALE'
  | 'RECEIPT'
  | 'CANCEL_SALE'
  | 'CANCEL_RECEIPT'
  | 'ADJUSTMENT';

export interface StockMovement {
  id: number;
  quantity: number | string;
  unit_cost: number | string | null;
  type: MovementType | string;
  ref_type: string;
  ref_id: number;
  balance_after: number | string;
  note: string | null;
  created_at: string;
}

export interface StockMovementsResponse {
  items: StockMovement[];
  pagination: Pagination;
}

export interface AdjustmentItemInput {
  product_id: number;
  new_quantity: number;
  reason?: string | null;
}

export interface AdjustmentResultItem {
  product_id: number;
  product_name: string;
  product_sku: string;
  old_quantity: number | string;
  new_quantity: number | string;
  delta: number | string;
  movement_id: number;
}

export interface AdjustmentResponse {
  items: AdjustmentResultItem[];
}

export interface AdjustmentMovement {
  id: number;
  product_id: number;
  product_name: string | null;
  product_sku: string | null;
  quantity: number | string;
  balance_after: number | string;
  note: string | null;
  created_at: string;
  created_by: number;
}

export interface AdjustmentMovementsResponse {
  items: AdjustmentMovement[];
  pagination: Pagination;
}

export interface ListInventoryParams {
  page?: number;
  limit?: number;
  search?: string;
  only_with_stock?: boolean;
}

export interface ListMovementsParams {
  page?: number;
  limit?: number;
}

export async function list(
  params: ListInventoryParams = {},
): Promise<InventoryListResponse> {
  const { data } = await apiClient.get<InventoryListResponse>('/inventory', {
    params,
  });
  return data;
}

export async function getLowStock(): Promise<LowStockResponse> {
  const { data } = await apiClient.get<LowStockResponse>('/inventory/low-stock');
  return data;
}

export async function getMovements(
  productId: number,
  params: ListMovementsParams = {},
): Promise<StockMovementsResponse> {
  const { data } = await apiClient.get<StockMovementsResponse>(
    `/inventory/${productId}/movements`,
    { params },
  );
  return data;
}

export async function createAdjustment(payload: {
  items: AdjustmentItemInput[];
}): Promise<AdjustmentResponse> {
  const { data } = await apiClient.post<AdjustmentResponse>(
    '/inventory/adjustments',
    payload,
  );
  return data;
}

export async function listAdjustments(
  params: ListMovementsParams = {},
): Promise<AdjustmentMovementsResponse> {
  const { data } = await apiClient.get<AdjustmentMovementsResponse>(
    '/inventory/adjustments',
    { params },
  );
  return data;
}
