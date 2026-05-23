import apiClient from './client';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface SupplierResponse {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  tax_code: string | null;
  note: string | null;
  total_debt: number | string;
  created_at: string;
  updated_at: string;
}

export interface SupplierListResponse {
  items: SupplierResponse[];
  pagination: Pagination;
}

export interface SupplierCreatePayload {
  name: string;
  phone?: string;
  email?: string;
  address?: string;
  tax_code?: string;
  note?: string;
}

export interface SupplierUpdatePayload {
  name?: string;
  phone?: string;
  email?: string;
  address?: string;
  tax_code?: string;
  note?: string;
}

export interface ListSuppliersParams {
  page?: number;
  limit?: number;
  search?: string;
}

export interface MessageResponse {
  message: string;
}

export async function listSuppliers(
  params: ListSuppliersParams = {},
): Promise<SupplierListResponse> {
  const { data } = await apiClient.get<SupplierListResponse>('/suppliers', { params });
  return data;
}

export async function getSupplier(id: number): Promise<SupplierResponse> {
  const { data } = await apiClient.get<SupplierResponse>(`/suppliers/${id}`);
  return data;
}

export async function createSupplier(
  payload: SupplierCreatePayload,
): Promise<SupplierResponse> {
  const { data } = await apiClient.post<SupplierResponse>('/suppliers', payload);
  return data;
}

export async function updateSupplier(
  id: number,
  payload: SupplierUpdatePayload,
): Promise<SupplierResponse> {
  const { data } = await apiClient.put<SupplierResponse>(`/suppliers/${id}`, payload);
  return data;
}

export async function deleteSupplier(id: number): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>(`/suppliers/${id}`);
  return data;
}
