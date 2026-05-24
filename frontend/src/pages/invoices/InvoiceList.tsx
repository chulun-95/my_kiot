import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as invoiceApi from '../../api/invoice';
import type {
  InvoiceBrief,
  InvoiceStatus,
  ListInvoicesParams,
} from '../../api/invoice';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';

const STATUS_LABEL: Record<InvoiceStatus, string> = {
  DRAFT: 'Nháp',
  COMPLETED: 'Đã hoàn tất',
  CANCELLED: 'Đã hủy',
};

export default function InvoiceList() {
  const [items, setItems] = useState<InvoiceBrief[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const params: ListInvoicesParams = { page, limit: 20 };
    if (statusFilter) params.status = statusFilter;
    invoiceApi
      .listInvoices(params)
      .then((res) => {
        setItems(res.items);
        setTotalPages(res.pagination.total_pages);
      })
      .catch((err) => setError(toFriendlyMessage(err)))
      .finally(() => setLoading(false));
  }, [page, statusFilter]);

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Hóa đơn</h1>
        <Link
          to="/pos"
          className="px-3 py-2 rounded bg-emerald-700 text-white text-sm"
        >
          Mở POS
        </Link>
      </div>

      <div className="bg-white border border-slate-200 rounded p-3 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-slate-600 mb-1">Trạng thái</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setPage(1);
              setStatusFilter(e.target.value as InvoiceStatus | '');
            }}
            aria-label="Lọc trạng thái"
            className="px-3 py-2 border border-slate-300 rounded"
          >
            <option value="">Tất cả</option>
            <option value="DRAFT">Nháp</option>
            <option value="COMPLETED">Đã hoàn tất</option>
            <option value="CANCELLED">Đã hủy</option>
          </select>
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
              <th className="px-3 py-2 text-left">Mã HĐ</th>
              <th className="px-3 py-2 text-left">Khách hàng</th>
              <th className="px-3 py-2 text-right">Tổng</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
              <th className="px-3 py-2 text-left">Hoàn tất lúc</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6">
                  <SkeletonRow count={5} />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6">
                  <EmptyState
                    title="Chưa có hóa đơn"
                    description="Mở POS để bắt đầu bán hàng."
                  />
                </td>
              </tr>
            ) : (
              items.map((it) => (
                <tr key={it.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono">
                    <Link to={`/invoices/${it.id}`} className="underline">
                      {it.code}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    {it.customer_name ?? 'Khách lẻ'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(it.total)}
                  </td>
                  <td className="px-3 py-2">{STATUS_LABEL[it.status]}</td>
                  <td className="px-3 py-2">
                    {it.completed_at ? formatDate(it.completed_at) : '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Trước
          </button>
          <span>
            Trang {page}/{totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      )}
    </div>
  );
}
