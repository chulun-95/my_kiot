import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const baseNav: Array<{ to: string; label: string }> = [
  { to: '/dashboard', label: 'Tổng quan' },
  { to: '/pos', label: 'Bán hàng (POS)' },
  { to: '/products', label: 'Sản phẩm' },
  { to: '/categories', label: 'Nhóm hàng' },
  { to: '/customers', label: 'Khách hàng' },
  { to: '/suppliers', label: 'Nhà cung cấp' },
  { to: '/goods-receipts', label: 'Nhập kho' },
  { to: '/inventory', label: 'Tồn kho' },
  { to: '/invoices', label: 'Hóa đơn' },
  { to: '/reports/revenue', label: 'Báo cáo' },
];

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const tenant = useAuthStore((s) => s.tenant);
  const doLogout = useAuthStore((s) => s.doLogout);
  const navigate = useNavigate();

  const navItems =
    user?.role === 'OWNER'
      ? [
          ...baseNav,
          { to: '/inventory/adjustments', label: 'Điều chỉnh kho' },
          { to: '/staff', label: 'Nhân viên' },
        ]
      : baseNav;

  const handleLogout = async () => {
    await doLogout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <aside className="w-60 shrink-0 bg-slate-900 text-slate-100 flex flex-col">
        <div className="px-4 py-4 text-lg font-semibold border-b border-slate-700">
          <Link to="/dashboard">my_kiot POS</Link>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm hover:bg-slate-800 ${isActive ? 'bg-slate-800 font-medium' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 px-4 flex items-center justify-between border-b border-slate-200 bg-white">
          <div className="text-sm text-slate-600">{tenant?.name ?? 'Chưa chọn shop'}</div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-700">{user?.full_name ?? 'Khách'}</span>
            <Link to="/me/change-password" className="text-slate-700 underline">
              Đổi mật khẩu
            </Link>
            <button
              onClick={handleLogout}
              className="px-3 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-slate-200"
            >
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
