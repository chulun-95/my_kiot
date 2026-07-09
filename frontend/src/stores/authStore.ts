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
  expires_at: string | null;
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
  initializing: boolean;
  setAuth: (payload: { user: User; tenant: Tenant; accessToken: string }) => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string | null) => void;
  logout: () => void;
  bootstrap: () => Promise<void>;
  login: (
    phone: string,
    password: string,
    tenantId?: number,
  ) => Promise<LoginPendingSelection | null>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  doLogout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  tenant: null,
  accessToken: null,
  initializing: true,
  setAuth: ({ user, tenant, accessToken }) => set({ user, tenant, accessToken }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  logout: () => set({ user: null, tenant: null, accessToken: null }),
  bootstrap: async () => {
    try {
      const res = await authApi.refresh();
      set({
        user: res.user,
        tenant: res.tenant,
        accessToken: res.access_token,
        initializing: false,
      });
    } catch {
      set({ user: null, tenant: null, accessToken: null, initializing: false });
    }
  },
  login: async (phone, password, tenantId) => {
    const res = await authApi.login({ phone, password, tenant_id: tenantId });
    if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
      return res;
    }
    const success = res as authApi.LoginSuccess;
    set({ user: success.user, tenant: success.tenant, accessToken: success.access_token });
    return null;
  },
  register: async (payload) => {
    const res = await authApi.register(payload);
    set({ user: res.user, tenant: res.tenant, accessToken: res.access_token });
  },
  doLogout: async () => {
    try {
      await authApi.logout();
    } catch {
      // swallow — luôn xóa state local
    }
    set({ user: null, tenant: null, accessToken: null });
  },
}));
