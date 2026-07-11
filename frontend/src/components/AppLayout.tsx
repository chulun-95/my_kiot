import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuthStore } from '../stores/authStore';

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
      aria-hidden
    >
      {children}
    </svg>
  );
}

const icons = {
  dashboard: (
    <Icon>
      <rect x="3" y="3" width="7" height="9" />
      <rect x="14" y="3" width="7" height="5" />
      <rect x="14" y="12" width="7" height="9" />
      <rect x="3" y="16" width="7" height="5" />
    </Icon>
  ),
  pos: (
    <Icon>
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.7 13.4a2 2 0 002 1.6h9.7a2 2 0 002-1.6L23 6H6" />
    </Icon>
  ),
  product: (
    <Icon>
      <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
      <path d="M3.27 6.96L12 12.01l8.73-5.05" />
      <path d="M12 22.08V12" />
    </Icon>
  ),
  category: (
    <Icon>
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </Icon>
  ),
  customer: (
    <Icon>
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87" />
      <path d="M16 3.13a4 4 0 010 7.75" />
    </Icon>
  ),
  supplier: (
    <Icon>
      <rect x="1" y="3" width="15" height="13" />
      <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
      <circle cx="5.5" cy="18.5" r="2.5" />
      <circle cx="18.5" cy="18.5" r="2.5" />
    </Icon>
  ),
  receipt: (
    <Icon>
      <path d="M21 8V21l-3-2-3 2-3-2-3 2-3-2-3 2V8" />
      <path d="M3 8a2 2 0 012-2h14a2 2 0 012 2" />
      <path d="M8 12h8" />
      <path d="M8 16h6" />
    </Icon>
  ),
  inventory: (
    <Icon>
      <path d="M3 9l9-6 9 6v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <rect x="9" y="13" width="6" height="8" />
      <path d="M3 13h6" />
      <path d="M15 13h6" />
    </Icon>
  ),
  invoice: (
    <Icon>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </Icon>
  ),
  revenue: (
    <Icon>
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </Icon>
  ),
  topProducts: (
    <Icon>
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </Icon>
  ),
  stockSummary: (
    <Icon>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
      <line x1="3" y1="20" x2="21" y2="20" />
    </Icon>
  ),
  profit: (
    <Icon>
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </Icon>
  ),
  adjustment: (
    <Icon>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </Icon>
  ),
  staff: (
    <Icon>
      <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 11l-3-3-3 3" />
      <path d="M19 8v6" />
    </Icon>
  ),
  user: (
    <Icon>
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </Icon>
  ),
  lock: (
    <Icon>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </Icon>
  ),
  logout: (
    <Icon>
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </Icon>
  ),
} as const;

const cashierNav: Array<{ to: string; label: string; icon: ReactNode }> = [
  { to: '/dashboard', label: 'Tổng quan', icon: icons.dashboard },
  { to: '/pos', label: 'Bán hàng (POS)', icon: icons.pos },
  { to: '/products', label: 'Sản phẩm', icon: icons.product },
  { to: '/categories', label: 'Nhóm hàng', icon: icons.category },
  { to: '/customers', label: 'Khách hàng', icon: icons.customer },
  { to: '/suppliers', label: 'Nhà cung cấp', icon: icons.supplier },
  { to: '/goods-receipts', label: 'Nhập kho', icon: icons.receipt },
  { to: '/inventory', label: 'Tồn kho', icon: icons.inventory },
  { to: '/invoices', label: 'Hóa đơn', icon: icons.invoice },
  { to: '/returns', label: 'Trả hàng', icon: icons.invoice },
];

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const tenant = useAuthStore((s) => s.tenant);
  const doLogout = useAuthStore((s) => s.doLogout);
  const navigate = useNavigate();

  const navItems =
    user?.role === 'OWNER'
      ? [
          ...cashierNav,
          { to: '/reports/revenue', label: 'Doanh thu', icon: icons.revenue },
          { to: '/reports/top-products', label: 'Top SP', icon: icons.topProducts },
          { to: '/reports/stock-summary', label: 'Tồn kho TQ', icon: icons.stockSummary },
          { to: '/reports/products-sold', label: 'SP đã bán', icon: icons.topProducts },
          { to: '/reports/profit', label: 'Lợi nhuận', icon: icons.profit },
          { to: '/reports/debts', label: 'Công nợ', icon: icons.customer },
          { to: '/reports/end-of-day', label: 'Cuối ngày', icon: icons.revenue },
          { to: '/cash-book', label: 'Sổ quỹ', icon: icons.revenue },
          { to: '/inventory/adjustments', label: 'Điều chỉnh kho', icon: icons.adjustment },
          { to: '/staff', label: 'Nhân viên', icon: icons.staff },
        ]
      : cashierNav;

  const handleLogout = async () => {
    await doLogout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <aside className="w-60 shrink-0 bg-slate-900 text-slate-100 flex flex-col">
        <div className="px-4 py-4 text-lg font-semibold border-b border-slate-700">
          <Link to="/dashboard">My-Kiot POS</Link>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2 text-sm hover:bg-slate-800 ${isActive ? 'bg-slate-800 font-medium' : ''}`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 px-4 flex items-center justify-between border-b border-slate-200 bg-white">
          <div className="text-sm text-slate-600">{tenant?.name ?? 'Chưa chọn shop'}</div>
          <div className="flex items-center gap-3 text-sm">
            <span className="flex items-center gap-1.5 text-slate-700">
              {icons.user}
              {user?.full_name ?? 'Khách'}
            </span>
            <Link to="/me/change-password" className="flex items-center gap-1.5 text-slate-700 underline">
              {icons.lock}
              Đổi mật khẩu
            </Link>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700"
            >
              {icons.logout}
              Đăng xuất
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
