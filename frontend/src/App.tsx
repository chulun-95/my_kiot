import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import RoleGate from './components/RoleGate';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ChangePassword from './pages/auth/ChangePassword';
import StaffList from './pages/staff/StaffList';
import ProductList from './pages/products/ProductList';
import ProductForm from './pages/products/ProductForm';
import ProductDetail from './pages/products/ProductDetail';
import CategoryTree from './pages/categories/CategoryTree';
import CustomerList from './pages/customers/CustomerList';
import CustomerForm from './pages/customers/CustomerForm';
import CustomerDetail from './pages/customers/CustomerDetail';
import SupplierList from './pages/suppliers/SupplierList';
import SupplierForm from './pages/suppliers/SupplierForm';
import GoodsReceiptList from './pages/goodsReceipts/GoodsReceiptList';
import GoodsReceiptForm from './pages/goodsReceipts/GoodsReceiptForm';
import GoodsReceiptDetail from './pages/goodsReceipts/GoodsReceiptDetail';
import InventoryList from './pages/inventory/InventoryList';
import LowStock from './pages/inventory/LowStock';
import Kardex from './pages/inventory/Kardex';
import AdjustmentList from './pages/inventory/AdjustmentList';
import AdjustmentForm from './pages/inventory/AdjustmentForm';
import POSScreen from './pages/pos/POSScreen';
import InvoiceList from './pages/invoices/InvoiceList';
import InvoiceDetail from './pages/invoices/InvoiceDetail';
import Dashboard from './pages/dashboard/Dashboard';
import RevenuePage from './pages/reports/RevenuePage';
import TopProductsPage from './pages/reports/TopProductsPage';
import ProfitPage from './pages/reports/ProfitPage';
import StockSummaryPage from './pages/reports/StockSummaryPage';

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

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
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
              <Route path="/inventory/low-stock" element={<LowStock />} />
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

              <Route path="/reports/revenue" element={<RevenuePage />} />
              <Route
                path="/reports/top-products"
                element={<TopProductsPage />}
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
      </BrowserRouter>
    </ErrorBoundary>
  );
}
