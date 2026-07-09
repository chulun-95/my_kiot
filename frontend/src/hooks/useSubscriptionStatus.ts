import { useAuthStore } from '../stores/authStore';

export interface SubscriptionStatus {
  isExpired: boolean;
  daysUntilExpiry: number | null;
}

const MS_PER_DAY = 86_400_000;

export function useSubscriptionStatus(): SubscriptionStatus {
  const tenant = useAuthStore((s) => s.tenant);
  if (!tenant?.expires_at) {
    return { isExpired: false, daysUntilExpiry: null };
  }
  const diffMs = new Date(tenant.expires_at).getTime() - Date.now();
  return {
    isExpired: diffMs <= 0,
    daysUntilExpiry: Math.ceil(diffMs / MS_PER_DAY),
  };
}
