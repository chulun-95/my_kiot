import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as customerApi from '../../api/customer';
import type { Pagination, CustomerResponse } from '../../api/customer';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function CustomerList() {
  const [items, setItems] = useState<CustomerResponse[]>([]);
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
      const res = await customerApi.listCustomers({
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Khách hàng</h1>
        <Link
          to="/customers/new"
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Thêm khách hàng
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
              <th className="px-3 py-2 text-right">Tổng chi tiêu</th>
              <th className="px-3 py-2 text-right">Số đơn</th>
              <th className="px-3 py-2 text-left">Lần mua cuối</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Chưa có khách hàng
                </td>
              </tr>
            ) : (
              items.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{c.name}</td>
                  <td className="px-3 py-2">{c.phone ?? '-'}</td>
                  <td className="px-3 py-2">{c.email ?? '-'}</td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(c.total_spent as number)}
                  </td>
                  <td className="px-3 py-2 text-right">{c.total_orders}</td>
                  <td className="px-3 py-2">
                    {c.last_order_at ? formatDate(c.last_order_at) : '-'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      to={`/customers/${c.id}`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block"
                    >
                      Xem
                    </Link>
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
          {pagination.total} khách hàng
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
