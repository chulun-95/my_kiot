import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as supplierApi from '../../api/supplier';
import type { Pagination, SupplierResponse } from '../../api/supplier';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';

export default function SupplierList() {
  const [items, setItems] = useState<SupplierResponse[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await supplierApi.listSuppliers({
        page,
        limit: 20,
        search: search || undefined,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
  }, [load]);

  const handleDelete = async (s: SupplierResponse) => {
    if (!confirm(`Xóa nhà cung cấp "${s.name}"?`)) return;
    try {
      await supplierApi.deleteSupplier(s.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Nhà cung cấp</h1>
        <Link
          to="/suppliers/new"
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Thêm nhà cung cấp
        </Link>
      </div>

      <input
        type="search"
        placeholder="Tìm theo tên hoặc SĐT..."
        value={search}
        onChange={(e) => {
          setPage(1);
          setSearch(e.target.value);
        }}
        className="w-full max-w-sm px-3 py-2 border border-slate-300 rounded"
      />

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">Tên</th>
              <th className="px-3 py-2 text-left">SĐT</th>
              <th className="px-3 py-2 text-left">Email</th>
              <th className="px-3 py-2 text-left">Mã số thuế</th>
              <th className="px-3 py-2 text-right">Công nợ</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6">
                  <SkeletonRow count={5} />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6">
                  <EmptyState
                    title="Chưa có nhà cung cấp"
                    description="Bấm 'Thêm nhà cung cấp' để bắt đầu."
                  />
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={s.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{s.name}</td>
                  <td className="px-3 py-2">{s.phone ?? '-'}</td>
                  <td className="px-3 py-2">{s.email ?? '-'}</td>
                  <td className="px-3 py-2">{s.tax_code ?? '-'}</td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(s.total_debt as number)}
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    <Link
                      to={`/suppliers/${s.id}/edit`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block"
                    >
                      Sửa
                    </Link>
                    <button
                      onClick={() => handleDelete(s)}
                      className="px-2 py-1 rounded border border-rose-300 text-rose-700"
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          Trang {pagination.page} / {Math.max(1, pagination.total_pages)} —{' '}
          {pagination.total} nhà cung cấp
        </span>
        <div className="space-x-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Trước
          </button>
          <button
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
