import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as goodsReceiptApi from '../../api/goodsReceipt';
import * as supplierApi from '../../api/supplier';
import type { GoodsReceiptBrief, Pagination, ReceiptStatus } from '../../api/goodsReceipt';
import type { SupplierResponse } from '../../api/supplier';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

function StatusBadge({ status }: { status: ReceiptStatus }) {
  if (status === 'COMPLETED') {
    return (
      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
        Hoàn tất
      </span>
    );
  }
  if (status === 'CANCELLED') {
    return (
      <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-700">
        Đã hủy
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700">
      Nháp
    </span>
  );
}

export default function GoodsReceiptList() {
  const [items, setItems] = useState<GoodsReceiptBrief[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [status, setStatus] = useState<ReceiptStatus | ''>('');
  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [suppliers, setSuppliers] = useState<SupplierResponse[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await supplierApi.listSuppliers({ limit: 100 });
        setSuppliers(res.items);
      } catch {
        // optional
      }
    })();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await goodsReceiptApi.list({
        page,
        limit: 20,
        status: status || undefined,
        supplier_id: supplierId === '' ? undefined : supplierId,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, status, supplierId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Phiếu nhập kho</h1>
        <Link
          to="/goods-receipts/new"
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Nhập hàng mới
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value as ReceiptStatus | '');
          }}
          className="px-3 py-2 border border-slate-300 rounded"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="DRAFT">Nháp</option>
          <option value="COMPLETED">Hoàn tất</option>
          <option value="CANCELLED">Đã hủy</option>
        </select>
        <select
          value={supplierId}
          onChange={(e) => {
            setPage(1);
            setSupplierId(e.target.value === '' ? '' : Number(e.target.value));
          }}
          className="px-3 py-2 border border-slate-300 rounded"
        >
          <option value="">Tất cả NCC</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
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
              <th className="px-3 py-2 text-left">Mã phiếu</th>
              <th className="px-3 py-2 text-left">NCC</th>
              <th className="px-3 py-2 text-right">Tổng tiền</th>
              <th className="px-3 py-2 text-right">Đã trả</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
              <th className="px-3 py-2 text-left">Hoàn tất lúc</th>
              <th className="px-3 py-2 text-left">Tạo lúc</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-slate-500">
                  Chưa có phiếu nhập
                </td>
              </tr>
            ) : (
              items.map((r) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                  <td className="px-3 py-2">{r.supplier_name ?? '-'}</td>
                  <td className="px-3 py-2 text-right">{formatVND(r.total as number)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(r.paid_amount as number)}</td>
                  <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                  <td className="px-3 py-2 text-slate-600">{formatDate(r.completed_at)}</td>
                  <td className="px-3 py-2 text-slate-600">{formatDate(r.created_at)}</td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      to={`/goods-receipts/${r.id}`}
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
          {pagination.total} phiếu
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
