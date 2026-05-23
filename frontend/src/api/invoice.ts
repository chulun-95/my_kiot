import apiClient from './client';

export type InvoiceStatus = 'DRAFT' | 'COMPLETED' | 'CANCELLED';
export type PaymentMethod =
  | 'CASH'
  | 'BANK_TRANSFER'
  | 'MOMO'
  | 'VNPAY'
  | 'OTHER';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface InvoiceItemInput {
  product_id: number;
  quantity: number;
  unit_price?: number;
  discount_amount?: number;
}

export interface InvoiceItemResponse {
  id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string | null;
  quantity: number | string;
  unit_price: number | string;
  cost_price: number | string;
  discount_amount: number | string;
  line_total: number | string;
}

export interface PaymentInput {
  method: PaymentMethod;
  amount: number;
  note?: string;
}

export interface PaymentResponse {
  id: number;
  method: PaymentMethod | string;
  amount: number | string;
  note: string | null;
  created_at: string;
}

export interface InvoiceBrief {
  id: number;
  code: string;
  customer_id: number | null;
  customer_name: string | null;
  cashier_id: number;
  total: number | string;
  paid_amount: number | string;
  status: InvoiceStatus;
  completed_at: string | null;
  created_at: string;
}

export interface InvoiceResponse {
  id: number;
  code: string;
  customer_id: number | null;
  customer_name: string | null;
  cashier_id: number;
  cashier_name: string | null;
  subtotal: number | string;
  discount_amount: number | string;
  total: number | string;
  cost_total: number | string;
  paid_amount: number | string;
  change_amount: number | string;
  status: InvoiceStatus;
  note: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  created_at: string;
  items: InvoiceItemResponse[];
  payments: PaymentResponse[];
}

export interface InvoiceListResponse {
  items: InvoiceBrief[];
  pagination: Pagination;
}

export interface InvoiceDraftListResponse {
  items: InvoiceBrief[];
}

export interface InvoiceCreatePayload {
  customer_id?: number | null;
  items: InvoiceItemInput[];
  discount_amount?: number;
  note?: string | null;
}

export interface InvoiceUpdatePayload {
  customer_id?: number | null;
  items?: InvoiceItemInput[];
  discount_amount?: number | null;
  note?: string | null;
}

export interface InvoiceCompletePayload {
  payments: PaymentInput[];
  allow_debt?: boolean;
}

export interface ListInvoicesParams {
  page?: number;
  limit?: number;
  status?: InvoiceStatus | '';
  customer_id?: number;
  cashier_id?: number;
}

export async function createDraft(
  payload: InvoiceCreatePayload,
): Promise<InvoiceResponse> {
  const { data } = await apiClient.post<InvoiceResponse>('/invoices', payload);
  return data;
}

export async function updateDraft(
  id: number,
  payload: InvoiceUpdatePayload,
): Promise<InvoiceResponse> {
  const { data } = await apiClient.put<InvoiceResponse>(
    `/invoices/${id}`,
    payload,
  );
  return data;
}

export async function getInvoice(id: number): Promise<InvoiceResponse> {
  const { data } = await apiClient.get<InvoiceResponse>(`/invoices/${id}`);
  return data;
}

export async function listInvoices(
  params: ListInvoicesParams = {},
): Promise<InvoiceListResponse> {
  const { data } = await apiClient.get<InvoiceListResponse>('/invoices', {
    params,
  });
  return data;
}

export async function listDrafts(
  mineOnly = true,
): Promise<InvoiceDraftListResponse> {
  const { data } = await apiClient.get<InvoiceDraftListResponse>(
    '/invoices/drafts',
    { params: { mine_only: mineOnly } },
  );
  return data;
}

export async function completeInvoice(
  id: number,
  payload: InvoiceCompletePayload,
): Promise<InvoiceResponse> {
  const { data } = await apiClient.post<InvoiceResponse>(
    `/invoices/${id}/complete`,
    payload,
  );
  return data;
}

export async function cancelInvoice(
  id: number,
  reason?: string,
): Promise<InvoiceResponse> {
  const { data } = await apiClient.post<InvoiceResponse>(
    `/invoices/${id}/cancel`,
    { reason },
  );
  return data;
}
