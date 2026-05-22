import type { ReactNode } from 'react';
import type { Role } from '../stores/authStore';
import { useAuthStore } from '../stores/authStore';

interface RoleGateProps {
  allow: Role[];
  fallback?: ReactNode;
  children: ReactNode;
}

export default function RoleGate({ allow, fallback = null, children }: RoleGateProps) {
  const role = useAuthStore((s) => s.user?.role);
  if (!role || !allow.includes(role)) return <>{fallback}</>;
  return <>{children}</>;
}
