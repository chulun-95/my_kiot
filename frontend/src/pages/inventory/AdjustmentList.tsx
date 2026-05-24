import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { AdjustmentMovement, Pagination } from '../../api/inventory';
import { formatDate, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function AdjustmentList() {
  const [items, setItems] = useState<AdjustmentMovement[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 50,
    total: 0,
    total_pages: 0,
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await inventoryApi.listAdjustments({ page, limit: 50 });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Điều chỉnh kho</h1>
        <Link
          to="/inventory/adjustments/new"
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Điều chỉnh mới
        </Link>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">Thời gian</th>
              <th className="px-3 py-2 text-left">Sản phẩm</th>
              <th className="px-3 py-2 text-right">SL thay đổi</th>
              <th className="px-3 py-2 text-right">Tồn sau</th>
              <th className="px-3 py-2 text-left">Lý do</th>
              <th className="px-3 py-2 text-right">Người tạo</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Chưa có điều chỉnh nào
                </td>
              </tr>
            ) : (
              items.map((m) => {
                const qty = Number(m.quantity);
                const positive = qty >= 0;
                return (
                  <tr key={m.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{formatDate(m.created_at)}</td>
                    <td className="px-3 py-2">
                      <span className="font-medium">{m.product_name ?? `SP #${m.product_id}`}</span>
                      {m.product_sku && (
                        <span className="ml-2 text-xs font-mono text-slate-500">
                          {m.product_sku}
                        </span>
                      )}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-medium ${
                        positive ? 'text-emerald-700' : 'text-rose-700'
                      }`}
                    >
                      {positive ? '+' : ''}
                      {formatQty(qty)}
                    </td>
                    <td className="px-3 py-2 text-right">{formatQty(m.balance_after as number)}</td>
                    <td className="px-3 py-2 text-slate-600">{m.note ?? ''}</td>
                    <td className="px-3 py-2 text-right text-slate-600">#{m.created_by}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          Trang {pagination.page} / {Math.max(1, pagination.total_pages)} —{' '}
          {pagination.total} mục
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
