import { create } from 'zustand';
import * as authApi from '../api/auth';

export type Role = 'OWNER' | 'CASHIER';

export interface User {
  id: number;
  full_name: string;
  role: Role;
  phone?: string | null;
  email?: string | null;
}

export interface Tenant {
  id: number;
  name: string;
  slug: string;
}

export interface TenantOption {
  id: number;
  name: string;
  role: Role;
}

export interface LoginPendingSelection {
  requires_tenant_selection: true;
  tenants: TenantOption[];
}

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (payload: {
    user: User;
    tenant: Tenant;
    accessToken: string;
    refreshToken: string;
  }) => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string | null) => void;
  logout: () => void;
  login: (
    phone: string,
    password: string,
    tenantId?: number,
  ) => Promise<LoginPendingSelection | null>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  doLogout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  tenant: null,
  accessToken: null,
  refreshToken: null,
  setAuth: ({ user, tenant, accessToken, refreshToken }) =>
    set({ user, tenant, accessToken, refreshToken }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  logout: () => set({ user: null, tenant: null, accessToken: null, refreshToken: null }),
  login: async (phone, password, tenantId) => {
    const res = await authApi.login({ phone, password, tenant_id: tenantId });
    if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
      return res;
    }
    const success = res as authApi.LoginSuccess;
    set({
      user: success.user,
      tenant: success.tenant,
      accessToken: success.access_token,
      refreshToken: success.refresh_token,
    });
    return null;
  },
  register: async (payload) => {
    const res = await authApi.register(payload);
    set({
      user: res.user,
      tenant: res.tenant,
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
    });
  },
  doLogout: async () => {
    const rt = get().refreshToken;
    if (rt) {
      try {
        await authApi.logout(rt);
      } catch {
        // swallow — always clear local state
      }
    }
    set({ user: null, tenant: null, accessToken: null, refreshToken: null });
  },
}));
