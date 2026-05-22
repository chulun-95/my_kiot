import apiClient from './client';
import type { Role } from '../stores/authStore';

export interface StaffResponse {
  id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface StaffListResponse {
  items: StaffResponse[];
  pagination: Pagination;
}

export interface ListParams {
  page?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}

export interface StaffCreatePayload {
  full_name: string;
  phone: string;
  email?: string;
  password: string;
}

export interface StaffUpdatePayload {
  full_name?: string;
  email?: string;
}

export async function listStaff(params: ListParams = {}): Promise<StaffListResponse> {
  const { data } = await apiClient.get<StaffListResponse>('/staff', { params });
  return data;
}

export async function createStaff(payload: StaffCreatePayload): Promise<StaffResponse> {
  const { data } = await apiClient.post<StaffResponse>('/staff', payload);
  return data;
}

export async function updateStaff(
  id: number,
  payload: StaffUpdatePayload,
): Promise<StaffResponse> {
  const { data } = await apiClient.put<StaffResponse>(`/staff/${id}`, payload);
  return data;
}

export async function deactivateStaff(id: number): Promise<StaffResponse> {
  const { data } = await apiClient.patch<StaffResponse>(`/staff/${id}/deactivate`);
  return data;
}

export async function activateStaff(id: number): Promise<StaffResponse> {
  const { data } = await apiClient.patch<StaffResponse>(`/staff/${id}/activate`);
  return data;
}
