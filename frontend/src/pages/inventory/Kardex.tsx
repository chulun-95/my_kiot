import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { Pagination, StockMovement } from '../../api/inventory';
import { formatDate, formatQty, formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

const TYPE_LABEL: Record<string, string> = {
  SALE: 'Bán hàng',
  RECEIPT: 'Nhập hàng',
  CANCEL_SALE: 'Hủy bán',
  CANCEL_RECEIPT: 'Hủy nhập',
  ADJUSTMENT: 'Điều chỉnh',
};

export default function Kardex() {
  const { productId } = useParams<{ productId: string }>();
  const [items, setItems] = useState<StockMovement[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 50,
    total: 0,
    total_pages: 0,
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await inventoryApi.getMovements(Number(productId), {
        page,
        limit: 50,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [productId, page]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/inventory" className="text-sm text-slate-600 hover:underline">
            ← Tồn kho
          </Link>
          <h1 className="text-2xl font-semibold mt-1">
            Thẻ kho — Sản phẩm #{productId}
          </h1>
        </div>
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
              <th className="px-3 py-2 text-left">Loại</th>
              <th className="px-3 py-2 text-left">Tham chiếu</th>
              <th className="px-3 py-2 text-right">SL thay đổi</th>
              <th className="px-3 py-2 text-right">Giá vốn / ĐV</th>
              <th className="px-3 py-2 text-right">Tồn sau</th>
              <th className="px-3 py-2 text-left">Ghi chú</th>
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
                  Chưa có giao dịch nào
                </td>
              </tr>
            ) : (
              items.map((m) => {
                const qty = Number(m.quantity);
                const positive = qty >= 0;
                return (
                  <tr key={m.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-700">{formatDate(m.created_at)}</td>
                    <td className="px-3 py-2">{TYPE_LABEL[m.type] ?? m.type}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {m.ref_type} #{m.ref_id}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-medium ${
                        positive ? 'text-emerald-700' : 'text-rose-700'
                      }`}
                    >
                      {positive ? '+' : ''}
                      {formatQty(qty)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {m.unit_cost == null ? '-' : formatVND(m.unit_cost as number)}
                    </td>
                    <td className="px-3 py-2 text-right">{formatQty(m.balance_after as number)}</td>
                    <td className="px-3 py-2 text-slate-600">{m.note ?? ''}</td>
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
          {pagination.total} giao dịch
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
