import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import dayjs from 'dayjs';
import * as cashApi from '../../api/cashbook';
import type { CashDirection, CashListResponse } from '../../api/cashbook';
import { CATEGORY_LABELS, METHOD_LABELS } from '../../api/cashbook';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

export default function CashBookList() {
  const today = dayjs().format('YYYY-MM-DD');
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [direction, setDirection] = useState<CashDirection | ''>('');
  const [data, setData] = useState<CashListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (f: string, t: string, dir: CashDirection | '') => {
    setLoading(true);
    setError(null);
    try {
      const res = await cashApi.listCash({
        from: f, to: t, ...(dir ? { direction: dir } : {}),
      });
      setData(res);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData(from, to, direction);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [direction]);

  const items = data?.items ?? [];
  const s = data?.summary;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sổ quỹ</h1>
        <Link to="/cash-book/new" className="px-3 py-2 rounded bg-slate-900 text-white text-sm">
          + Lập phiếu thu/chi
        </Link>
      </div>

      {s && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-sm text-slate-500">Tổng thu (kỳ)</div>
            <div className="text-xl font-semibold text-emerald-700">{formatVND(s.range_in)}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-sm text-slate-500">Tổng chi (kỳ)</div>
            <div className="text-xl font-semibold text-rose-700">{formatVND(s.range_out)}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-sm text-slate-500">Tồn quỹ hiện tại</div>
            <div className="text-xl font-semibold">{formatVND(s.balance_total)}</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Từ ngày</span>
          <input type="date" aria-label="Từ ngày" value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1" />
        </label>
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Đến ngày</span>
          <input type="date" aria-label="Đến ngày" value={to}
            onChange={(e) => setTo(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1" />
        </label>
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Loại</span>
          <select aria-label="Loại" value={direction}
            onChange={(e) => setDirection(e.target.value as CashDirection | '')}
            className="border border-slate-300 rounded px-2 py-1">
            <option value="">Tất cả</option>
            <option value="IN">Phiếu thu</option>
            <option value="OUT">Phiếu chi</option>
          </select>
        </label>
        <button onClick={() => fetchData(from, to, direction)}
          className="px-3 py-2 rounded bg-slate-900 text-white">Xem</button>
      </div>

      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}

      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        {loading ? (
          <div className="p-4"><SkeletonCard /></div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Mã phiếu</th>
                <th className="px-3 py-2 text-left">Thời gian</th>
                <th className="px-3 py-2 text-left">Loại</th>
                <th className="px-3 py-2 text-left">Phương thức</th>
                <th className="px-3 py-2 text-right">Thu</th>
                <th className="px-3 py-2 text-right">Chi</th>
                <th className="px-3 py-2 text-left">Ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={7} className="px-3 py-6"><EmptyState title="Chưa có phiếu thu/chi" /></td></tr>
              ) : (
                items.map((it) => (
                  <tr key={it.id} className={`border-t border-slate-100 ${it.status === 'CANCELLED' ? 'opacity-40 line-through' : ''}`}>
                    <td className="px-3 py-2 font-mono text-xs">{it.code}</td>
                    <td className="px-3 py-2">{formatDate(it.created_at)}</td>
                    <td className="px-3 py-2">{CATEGORY_LABELS[it.category] ?? it.category}</td>
                    <td className="px-3 py-2">{METHOD_LABELS[it.method]}</td>
                    <td className="px-3 py-2 text-right text-emerald-700">
                      {it.direction === 'IN' ? formatVND(it.amount) : ''}
                    </td>
                    <td className="px-3 py-2 text-right text-rose-700">
                      {it.direction === 'OUT' ? formatVND(it.amount) : ''}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{it.note}</td>
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
