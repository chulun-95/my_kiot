import apiClient from './client';

export type ReceiptStatus = 'DRAFT' | 'COMPLETED' | 'CANCELLED';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface GoodsReceiptItemInput {
  product_id: number;
  quantity: number;
  cost_price: number;
}

export interface GoodsReceiptItemResponse {
  id: number;
  product_id: number;
  product_name: string | null;
  product_sku: string | null;
  quantity: number | string;
  cost_price: number | string;
  line_total: number | string;
}

export interface GoodsReceiptBrief {
  id: number;
  code: string;
  supplier_id: number | null;
  supplier_name: string | null;
  total: number | string;
  paid_amount: number | string;
  status: ReceiptStatus;
  completed_at: string | null;
  created_at: string;
}

export interface GoodsReceiptResponse {
  id: number;
  code: string;
  supplier_id: number | null;
  supplier_name: string | null;
  total: number | string;
  paid_amount: number | string;
  status: ReceiptStatus;
  note: string | null;
  completed_at: string | null;
  created_at: string;
  items: GoodsReceiptItemResponse[];
}

export interface GoodsReceiptListResponse {
  items: GoodsReceiptBrief[];
  pagination: Pagination;
}

export interface GoodsReceiptCreatePayload {
  supplier_id?: number | null;
  items: GoodsReceiptItemInput[];
  paid_amount?: number;
  note?: string | null;
}

export interface GoodsReceiptUpdatePayload {
  supplier_id?: number | null;
  items?: GoodsReceiptItemInput[];
  paid_amount?: number | null;
  note?: string | null;
}

export interface ListReceiptsParams {
  page?: number;
  limit?: number;
  status?: ReceiptStatus | '';
  supplier_id?: number;
}

export async function list(
  params: ListReceiptsParams = {},
): Promise<GoodsReceiptListResponse> {
  const { data } = await apiClient.get<GoodsReceiptListResponse>(
    '/goods-receipts',
    { params },
  );
  return data;
}

export async function get(id: number): Promise<GoodsReceiptResponse> {
  const { data } = await apiClient.get<GoodsReceiptResponse>(
    `/goods-receipts/${id}`,
  );
  return data;
}

export async function create(
  payload: GoodsReceiptCreatePayload,
): Promise<GoodsReceiptResponse> {
  const { data } = await apiClient.post<GoodsReceiptResponse>(
    '/goods-receipts',
    payload,
  );
  return data;
}

export async function update(
  id: number,
  payload: GoodsReceiptUpdatePayload,
): Promise<GoodsReceiptResponse> {
  const { data } = await apiClient.put<GoodsReceiptResponse>(
    `/goods-receipts/${id}`,
    payload,
  );
  return data;
}

export async function complete(id: number): Promise<GoodsReceiptResponse> {
  const { data } = await apiClient.post<GoodsReceiptResponse>(
    `/goods-receipts/${id}/complete`,
  );
  return data;
}

export async function cancel(
  id: number,
  reason?: string,
): Promise<GoodsReceiptResponse> {
  const { data } = await apiClient.post<GoodsReceiptResponse>(
    `/goods-receipts/${id}/cancel`,
    { reason },
  );
  return data;
}
