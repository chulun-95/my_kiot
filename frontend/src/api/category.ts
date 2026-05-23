import apiClient from './client';

export interface CategoryResponse {
  id: number;
  name: string;
  parent_id: number | null;
  depth: number;
  sort_order: number;
  created_at: string;
}

export interface CategoryNode {
  id: number;
  name: string;
  depth: number;
  sort_order: number;
  children: CategoryNode[];
}

export interface CategoryTreeResponse {
  items: CategoryNode[];
}

export interface CategoryCreatePayload {
  name: string;
  parent_id?: number | null;
  sort_order?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  parent_id?: number | null;
  sort_order?: number;
}

export interface MessageResponse {
  message: string;
}

export async function listCategories(): Promise<CategoryTreeResponse> {
  const { data } = await apiClient.get<CategoryTreeResponse>('/categories');
  return data;
}

export async function createCategory(
  payload: CategoryCreatePayload,
): Promise<CategoryResponse> {
  const { data } = await apiClient.post<CategoryResponse>('/categories', payload);
  return data;
}

export async function updateCategory(
  id: number,
  payload: CategoryUpdatePayload,
): Promise<CategoryResponse> {
  const { data } = await apiClient.put<CategoryResponse>(`/categories/${id}`, payload);
  return data;
}

export async function deleteCategory(id: number): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>(`/categories/${id}`);
  return data;
}
