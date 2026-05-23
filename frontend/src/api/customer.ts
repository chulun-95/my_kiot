import apiClient from './client';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface CustomerResponse {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  note: string | null;
  total_spent: number | string;
  total_orders: number;
  last_order_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerOrderHistoryItem {
  invoice_id: number;
  code: string;
  total: number | string;
  completed_at: string | null;
  status: string;
}

export interface CustomerDetailResponse {
  customer: CustomerResponse;
  recent_orders: CustomerOrderHistoryItem[];
}

export interface CustomerListResponse {
  items: CustomerResponse[];
  pagination: Pagination;
}

export interface CustomerCreatePayload {
  name: string;
  phone?: string;
  email?: string;
  address?: string;
  note?: string;
}

export interface CustomerUpdatePayload {
  name?: string;
  phone?: string;
  email?: string;
  address?: string;
  note?: string;
}

export interface ListCustomersParams {
  page?: number;
  limit?: number;
  search?: string;
}

export interface MessageResponse {
  message: string;
}

export async function listCustomers(
  params: ListCustomersParams = {},
): Promise<CustomerListResponse> {
  const { data } = await apiClient.get<CustomerListResponse>('/customers', { params });
  return data;
}

export async function getCustomer(id: number): Promise<CustomerDetailResponse> {
  const { data } = await apiClient.get<CustomerDetailResponse>(`/customers/${id}`);
  return data;
}

export async function createCustomer(
  payload: CustomerCreatePayload,
): Promise<CustomerResponse> {
  const { data } = await apiClient.post<CustomerResponse>('/customers', payload);
  return data;
}

export async function updateCustomer(
  id: number,
  payload: CustomerUpdatePayload,
): Promise<CustomerResponse> {
  const { data } = await apiClient.put<CustomerResponse>(`/customers/${id}`, payload);
  return data;
}

export async function deleteCustomer(id: number): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>(`/customers/${id}`);
  return data;
}

export async function getCustomerByPhone(phone: string): Promise<CustomerResponse> {
  const { data } = await apiClient.get<CustomerResponse>(
    `/customers/phone/${encodeURIComponent(phone)}`,
  );
  return data;
}
