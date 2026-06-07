import apiClient from './client';

export type CashDirection = 'IN' | 'OUT';
export type CashMethod = 'CASH' | 'BANK_TRANSFER' | 'EWALLET';
export type CashStatus = 'ACTIVE' | 'CANCELLED';

export interface CashTransaction {
  id: number;
  code: string;
  direction: CashDirection;
  method: CashMethod;
  category: string;
  amount: number | string;
  ref_type: string;
  ref_id: number | null;
  partner_type: string | null;
  partner_id: number | null;
  partner_name: string | null;
  note: string | null;
  status: CashStatus;
  created_at: string;
  created_by: number | null;
}

export interface MethodBalance {
  method: CashMethod;
  balance: number | string;
}

export interface CashSummary {
  range_in: number | string;
  range_out: number | string;
  balance_total: number | string;
  balance_by_method: MethodBalance[];
}

export interface CashPagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface CashListResponse {
  items: CashTransaction[];
  summary: CashSummary;
  pagination: CashPagination;
}

export interface CashListParams {
  direction?: CashDirection;
  method?: CashMethod;
  category?: string;
  ref_type?: string;
  from?: string;
  to?: string;
  page?: number;
  limit?: number;
}

export interface CashCreatePayload {
  direction: CashDirection;
  method: CashMethod;
  category: string;
  amount: number;
  partner_type?: 'CUSTOMER' | 'SUPPLIER' | 'OTHER';
  partner_id?: number;
  partner_name?: string;
  note?: string;
}

export async function listCash(params: CashListParams = {}): Promise<CashListResponse> {
  const { data } = await apiClient.get<CashListResponse>('/cash-transactions', { params });
  return data;
}

export async function createCash(payload: CashCreatePayload): Promise<CashTransaction> {
  const { data } = await apiClient.post<CashTransaction>('/cash-transactions', payload);
  return data;
}

export async function cancelCash(id: number, reason?: string): Promise<CashTransaction> {
  const { data } = await apiClient.post<CashTransaction>(`/cash-transactions/${id}/cancel`, { reason });
  return data;
}

export const CATEGORY_LABELS: Record<string, string> = {
  SALE: 'Thu bán hàng',
  OTHER_IN: 'Thu khác',
  CAPITAL: 'Góp vốn',
  PURCHASE: 'Chi nhập hàng',
  CHANGE: 'Tiền thối',
  SALARY: 'Chi lương',
  OPERATING: 'Chi phí vận hành',
  OTHER_OUT: 'Chi khác',
};

export const METHOD_LABELS: Record<CashMethod, string> = {
  CASH: 'Tiền mặt',
  BANK_TRANSFER: 'Chuyển khoản',
  EWALLET: 'Ví điện tử',
};
