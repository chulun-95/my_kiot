import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import RoleGate from './components/RoleGate';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ChangePassword from './pages/auth/ChangePassword';
import StaffList from './pages/staff/StaffList';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
}

function NotFound() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">404 — Không tìm thấy trang</h1>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Placeholder title="Tổng quan" />} />
              <Route path="/pos" element={<Placeholder title="Bán hàng (POS)" />} />
              <Route path="/products" element={<Placeholder title="Sản phẩm" />} />
              <Route path="/categories" element={<Placeholder title="Nhóm hàng" />} />
              <Route path="/customers" element={<Placeholder title="Khách hàng" />} />
              <Route path="/suppliers" element={<Placeholder title="Nhà cung cấp" />} />
              <Route path="/inventory" element={<Placeholder title="Tồn kho" />} />
              <Route path="/invoices" element={<Placeholder title="Hóa đơn" />} />
              <Route
                path="/reports/revenue"
                element={<Placeholder title="Báo cáo doanh thu" />}
              />
              <Route path="/me/change-password" element={<ChangePassword />} />
              <Route
                path="/staff"
                element={
                  <RoleGate
                    allow={['OWNER']}
                    fallback={
                      <h1 className="text-2xl font-semibold">Không có quyền truy cập</h1>
                    }
                  >
                    <StaffList />
                  </RoleGate>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
