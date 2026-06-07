import apiClient from './client';

export interface ReturnableLine {
  invoice_item_id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string | null;
  sold_quantity: number | string;
  returned_quantity: number | string;
  returnable_quantity: number | string;
  unit_price: number | string;
}
export interface ReturnableInvoice {
  invoice_id: number;
  invoice_code: string;
  customer_id: number | null;
  customer_name: string | null;
  lines: ReturnableLine[];
}
export interface ReturnListItem {
  id: number;
  code: string;
  invoice_id: number;
  customer_name: string | null;
  total_refund: number | string;
  refund_method: string;
  status: string;
  completed_at: string | null;
}
export interface ReturnListResponse {
  items: ReturnListItem[];
  pagination: { page: number; limit: number; total: number; total_pages: number };
}
export interface ReturnCreatePayload {
  invoice_id: number;
  items: { invoice_item_id: number; quantity: number }[];
  refund_method: 'CASH' | 'BANK_TRANSFER' | 'EWALLET';
  reason?: string;
}

export async function listReturns(params: { page?: number; limit?: number } = {}): Promise<ReturnListResponse> {
  const { data } = await apiClient.get<ReturnListResponse>('/returns', { params });
  return data;
}

export async function getReturnable(invoiceId: number): Promise<ReturnableInvoice> {
  const { data } = await apiClient.get<ReturnableInvoice>(`/returns/returnable/${invoiceId}`);
  return data;
}

export async function createReturn(payload: ReturnCreatePayload) {
  const { data } = await apiClient.post('/returns', payload);
  return data;
}

export async function cancelReturn(id: number, reason?: string) {
  const { data } = await apiClient.post(`/returns/${id}/cancel`, { reason });
  return data;
}
