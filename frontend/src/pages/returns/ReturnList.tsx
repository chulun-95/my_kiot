import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as api from '../../api/salesReturn';
import type { ReturnListResponse } from '../../api/salesReturn';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

export default function ReturnList() {
  const [data, setData] = useState<ReturnListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .listReturns()
      .then(setData)
      .catch((e) => setError(toFriendlyMessage(e)))
      .finally(() => setLoading(false));
  }, []);
  const items = data?.items ?? [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Trả hàng</h1>
      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}
      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        {loading ? (
          <div className="p-4">
            <SkeletonCard />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Mã phiếu</th>
                <th className="px-3 py-2 text-left">Hóa đơn</th>
                <th className="px-3 py-2 text-left">Thời gian</th>
                <th className="px-3 py-2 text-right">Hoàn tiền</th>
                <th className="px-3 py-2 text-left">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-6">
                    <EmptyState title="Chưa có phiếu trả hàng" />
                  </td>
                </tr>
              ) : (
                items.map((it) => (
                  <tr
                    key={it.id}
                    className={`border-t border-slate-100 ${it.status === 'CANCELLED' ? 'opacity-40 line-through' : ''}`}
                  >
                    <td className="px-3 py-2 font-mono text-xs">
                      <Link to={`/returns/${it.id}`} className="text-slate-900 underline">
                        {it.code}
                      </Link>
                    </td>
                    <td className="px-3 py-2">#{it.invoice_id}</td>
                    <td className="px-3 py-2">{formatDate(it.completed_at)}</td>
                    <td className="px-3 py-2 text-right text-rose-700">{formatVND(it.total_refund)}</td>
                    <td className="px-3 py-2">{it.status === 'COMPLETED' ? 'Đã trả' : 'Đã hủy'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
