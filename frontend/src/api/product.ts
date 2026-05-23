import apiClient from './client';

export type ProductStatus = 'ACTIVE' | 'INACTIVE' | 'DRAFT';

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface ProductResponse {
  id: number;
  sku: string;
  barcode: string | null;
  name: string;
  description: string | null;
  unit: string;
  cost_price: number | string | null;
  sale_price: number | string;
  min_stock: number;
  image_url: string | null;
  status: ProductStatus;
  allow_negative: boolean;
  category_id: number | null;
  category_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductBrief {
  id: number;
  sku: string;
  barcode: string | null;
  name: string;
  unit: string;
  sale_price: number | string;
  cost_price: number | string | null;
  image_url: string | null;
  allow_negative: boolean;
  status: ProductStatus;
}

export interface ProductListResponse {
  items: ProductResponse[];
  pagination: Pagination;
}

export interface ProductSearchResponse {
  items: ProductBrief[];
}

export interface MessageResponse {
  message: string;
}

export interface ListProductsParams {
  page?: number;
  limit?: number;
  search?: string;
  category_id?: number;
  status?: ProductStatus | '';
}

export interface ProductCreatePayload {
  name: string;
  sku?: string;
  barcode?: string;
  category_id?: number | null;
  description?: string;
  unit?: string;
  cost_price?: number;
  sale_price?: number;
  min_stock?: number;
  image_url?: string;
  status?: ProductStatus;
  allow_negative?: boolean;
}

export interface ProductUpdatePayload {
  name?: string;
  sku?: string;
  barcode?: string;
  category_id?: number | null;
  description?: string;
  unit?: string;
  cost_price?: number;
  sale_price?: number;
  min_stock?: number;
  image_url?: string;
  status?: ProductStatus;
  allow_negative?: boolean;
}

export async function listProducts(
  params: ListProductsParams = {},
): Promise<ProductListResponse> {
  const { data } = await apiClient.get<ProductListResponse>('/products', { params });
  return data;
}

export async function getProduct(id: number): Promise<ProductResponse> {
  const { data } = await apiClient.get<ProductResponse>(`/products/${id}`);
  return data;
}

export async function createProduct(
  payload: ProductCreatePayload,
): Promise<ProductResponse> {
  const { data } = await apiClient.post<ProductResponse>('/products', payload);
  return data;
}

export async function updateProduct(
  id: number,
  payload: ProductUpdatePayload,
): Promise<ProductResponse> {
  const { data } = await apiClient.put<ProductResponse>(`/products/${id}`, payload);
  return data;
}

export async function deleteProduct(id: number): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>(`/products/${id}`);
  return data;
}

export async function searchProducts(
  q: string,
  limit = 20,
): Promise<ProductSearchResponse> {
  const { data } = await apiClient.get<ProductSearchResponse>('/products/search', {
    params: { q, limit },
  });
  return data;
}

export async function getProductByBarcode(code: string): Promise<ProductBrief> {
  const { data } = await apiClient.get<ProductBrief>(
    `/products/barcode/${encodeURIComponent(code)}`,
  );
  return data;
}
