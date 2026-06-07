import apiClient from './client';
import type { Role, Tenant, User, TenantOption, LoginPendingSelection } from '../stores/authStore';

export interface RegisterPayload {
  shop_name: string;
  owner_name: string;
  phone: string;
  email?: string;
  password: string;
}

export interface LoginPayload {
  phone: string;
  password: string;
  tenant_id?: number;
}

export interface LoginSuccess {
  user: User;
  tenant: Tenant;
  access_token: string;
  refresh_token?: string;
}

export type AuthSuccess = LoginSuccess;

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface MeResponse {
  user: User;
  tenant: Tenant;
}

export async function register(payload: RegisterPayload): Promise<AuthSuccess> {
  const { data } = await apiClient.post<AuthSuccess>('/auth/register', payload);
  return data;
}

export async function login(
  payload: LoginPayload,
): Promise<LoginSuccess | LoginPendingSelection> {
  const { data } = await apiClient.post<LoginSuccess | LoginPendingSelection>(
    '/auth/login',
    payload,
  );
  return data;
}

export async function refresh(): Promise<LoginSuccess> {
  const { data } = await apiClient.post<LoginSuccess>('/auth/refresh', {});
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout', {});
}

export async function me(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/auth/me');
  return data;
}

export async function changePassword(payload: ChangePasswordPayload): Promise<TokenPair> {
  const { data } = await apiClient.put<TokenPair>('/auth/change-password', payload);
  return data;
}

export type { Role, User, Tenant, TenantOption };
