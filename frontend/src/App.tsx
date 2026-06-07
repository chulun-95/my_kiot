import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import RoleGate from './components/RoleGate';

const Login = lazy(() => import('./pages/auth/Login'));
const Register = lazy(() => import('./pages/auth/Register'));
const ChangePassword = lazy(() => import('./pages/auth/ChangePassword'));
const StaffList = lazy(() => import('./pages/staff/StaffList'));
const ProductList = lazy(() => import('./pages/products/ProductList'));
const ProductForm = lazy(() => import('./pages/products/ProductForm'));
const ProductDetail = lazy(() => import('./pages/products/ProductDetail'));
const CategoryTree = lazy(() => import('./pages/categories/CategoryTree'));
const CustomerList = lazy(() => import('./pages/customers/CustomerList'));
const CustomerForm = lazy(() => import('./pages/customers/CustomerForm'));
const CustomerDetail = lazy(() => import('./pages/customers/CustomerDetail'));
const SupplierList = lazy(() => import('./pages/suppliers/SupplierList'));
const SupplierForm = lazy(() => import('./pages/suppliers/SupplierForm'));
const GoodsReceiptList = lazy(() => import('./pages/goodsReceipts/GoodsReceiptList'));
const GoodsReceiptForm = lazy(() => import('./pages/goodsReceipts/GoodsReceiptForm'));
const GoodsReceiptDetail = lazy(() => import('./pages/goodsReceipts/GoodsReceiptDetail'));
const InventoryList = lazy(() => import('./pages/inventory/InventoryList'));
const LowStock = lazy(() => import('./pages/inventory/LowStock'));
const Kardex = lazy(() => import('./pages/inventory/Kardex'));
const AdjustmentList = lazy(() => import('./pages/inventory/AdjustmentList'));
const AdjustmentForm = lazy(() => import('./pages/inventory/AdjustmentForm'));
const POSScreen = lazy(() => import('./pages/pos/POSScreen'));
const InvoiceList = lazy(() => import('./pages/invoices/InvoiceList'));
const InvoiceDetail = lazy(() => import('./pages/invoices/InvoiceDetail'));
const Dashboard = lazy(() => import('./pages/dashboard/Dashboard'));
const RevenuePage = lazy(() => import('./pages/reports/RevenuePage'));
const TopProductsPage = lazy(() => import('./pages/reports/TopProductsPage'));
const ProductsSoldPage = lazy(() => import('./pages/reports/ProductsSoldPage'));
const ProfitPage = lazy(() => import('./pages/reports/ProfitPage'));
const StockSummaryPage = lazy(() => import('./pages/reports/StockSummaryPage'));
const DebtReportPage = lazy(() => import('./pages/reports/DebtReportPage'));
const CashBookList = lazy(() => import('./pages/cashbook/CashBookList'));
const CashVoucherForm = lazy(() => import('./pages/cashbook/CashVoucherForm'));
const ReturnList = lazy(() => import('./pages/returns/ReturnList'));
const ReturnForm = lazy(() => import('./pages/returns/ReturnForm'));

function NotFound() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">404 — Không tìm thấy trang</h1>
    </div>
  );
}

function OwnerOnly({ children }: { children: React.ReactNode }) {
  return (
    <RoleGate
      allow={['OWNER']}
      fallback={<h1 className="text-2xl font-semibold">Không có quyền truy cập</h1>}
    >
      {children}
    </RoleGate>
  );
}

function PageFallback() {
  return <div className="p-6 text-gray-400">Đang tải...</div>;
}

export default function App() {
  const initializing = useAuthStore((s) => s.initializing);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  if (initializing) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-500">
        Đang tải...
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/pos" element={<POSScreen />} />
              <Route element={<AppLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />

                <Route path="/products" element={<ProductList />} />
                <Route path="/products/new" element={<ProductForm />} />
                <Route path="/products/:id" element={<ProductDetail />} />
                <Route path="/products/:id/edit" element={<ProductForm />} />

                <Route path="/categories" element={<CategoryTree />} />

                <Route path="/customers" element={<CustomerList />} />
                <Route path="/customers/new" element={<CustomerForm mode="create" />} />
                <Route path="/customers/:id" element={<CustomerDetail />} />

                <Route path="/suppliers" element={<SupplierList />} />
                <Route path="/suppliers/new" element={<SupplierForm />} />
                <Route path="/suppliers/:id/edit" element={<SupplierForm />} />

                <Route path="/goods-receipts" element={<GoodsReceiptList />} />
                <Route path="/goods-receipts/new" element={<GoodsReceiptForm />} />
                <Route path="/goods-receipts/:id" element={<GoodsReceiptDetail />} />

                <Route path="/inventory" element={<InventoryList />} />
                <Route
                  path="/inventory/low-stock"
                  element={
                    <OwnerOnly>
                      <LowStock />
                    </OwnerOnly>
                  }
                />
                <Route
                  path="/inventory/:productId/movements"
                  element={<Kardex />}
                />
                <Route
                  path="/inventory/adjustments"
                  element={
                    <OwnerOnly>
                      <AdjustmentList />
                    </OwnerOnly>
                  }
                />
                <Route
                  path="/inventory/adjustments/new"
                  element={
                    <OwnerOnly>
                      <AdjustmentForm />
                    </OwnerOnly>
                  }
                />

                <Route path="/invoices" element={<InvoiceList />} />
                <Route path="/invoices/:id" element={<InvoiceDetail />} />

                <Route path="/returns" element={<ReturnList />} />
                <Route path="/returns/new" element={<ReturnForm />} />

                <Route path="/reports/revenue" element={<RevenuePage />} />
                <Route
                  path="/reports/top-products"
                  element={<TopProductsPage />}
                />
                <Route
                  path="/reports/products-sold"
                  element={
                    <OwnerOnly>
                      <ProductsSoldPage />
                    </OwnerOnly>
                  }
                />
                <Route
                  path="/reports/profit"
                  element={
                    <OwnerOnly>
                      <ProfitPage />
                    </OwnerOnly>
                  }
                />
                <Route
                  path="/reports/stock-summary"
                  element={<StockSummaryPage />}
                />
                <Route
                  path="/reports/debts"
                  element={
                    <OwnerOnly>
                      <DebtReportPage />
                    </OwnerOnly>
                  }
                />

                <Route path="/cash-book" element={<OwnerOnly><CashBookList /></OwnerOnly>} />
                <Route path="/cash-book/new" element={<OwnerOnly><CashVoucherForm /></OwnerOnly>} />

                <Route path="/me/change-password" element={<ChangePassword />} />
                <Route
                  path="/staff"
                  element={
                    <OwnerOnly>
                      <StaffList />
                    </OwnerOnly>
                  }
                />
              </Route>
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
