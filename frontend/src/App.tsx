import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
}

function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm p-6 bg-white rounded shadow border border-slate-200">
        <h1 className="text-xl font-semibold mb-2">Đăng nhập</h1>
        <p className="text-sm text-slate-600">Form đăng nhập sẽ được triển khai ở Phase 1.</p>
      </div>
    </div>
  );
}

function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-md p-6 bg-white rounded shadow border border-slate-200">
        <h1 className="text-xl font-semibold mb-2">Đăng ký shop</h1>
        <p className="text-sm text-slate-600">Form đăng ký sẽ được triển khai ở Phase 1.</p>
      </div>
    </div>
  );
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
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
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
              <Route path="/reports/revenue" element={<Placeholder title="Báo cáo doanh thu" />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
