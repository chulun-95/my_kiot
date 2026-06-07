import { useCallback, useEffect, useState } from 'react';
import dayjs from 'dayjs';
import * as reportApi from '../../api/report';
import type { EndOfDayResponse } from '../../api/report';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import { SkeletonCard } from '../../components/Skeleton';

const METHOD_LABELS: Record<string, string> = {
  CASH: 'Tiền mặt', BANK_TRANSFER: 'Chuyển khoản', EWALLET: 'Ví điện tử',
};

export default function EndOfDayPage() {
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [data, setData] = useState<EndOfDayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (d: string) => {
    setLoading(true); setError(null);
    try { setData(await reportApi.getEndOfDay(d)); }
    catch (e) { setError(toFriendlyMessage(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(date); /* eslint-disable-next-line */ }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Báo cáo cuối ngày</h1>
      <div className="flex items-end gap-3">
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Ngày</span>
          <input type="date" aria-label="Ngày" value={date}
            onChange={(e) => setDate(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1" />
        </label>
        <button onClick={() => load(date)} className="px-3 py-2 rounded bg-slate-900 text-white">Xem</button>
      </div>

      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}

      {loading ? <SkeletonCard /> : data && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Doanh thu bán hàng</div>
              <div className="text-xl font-semibold">{formatVND(data.sales_revenue)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Số hóa đơn</div>
              <div className="text-xl font-semibold">{data.sales_invoices}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Tồn quỹ cuối ngày</div>
              <div className="text-xl font-semibold">{formatVND(data.closing_total)}</div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600"><tr>
                <th className="px-3 py-2 text-left">Phương thức</th>
                <th className="px-3 py-2 text-right">Tồn đầu ngày</th>
                <th className="px-3 py-2 text-right">Thu</th>
                <th className="px-3 py-2 text-right">Chi</th>
                <th className="px-3 py-2 text-right">Tồn cuối ngày</th>
              </tr></thead>
              <tbody>
                {data.by_method.map((m) => (
                  <tr key={m.method} className="border-t border-slate-100">
                    <td className="px-3 py-2">{METHOD_LABELS[m.method] ?? m.method}</td>
                    <td className="px-3 py-2 text-right">{formatVND(m.opening)}</td>
                    <td className="px-3 py-2 text-right text-emerald-700">{formatVND(m.total_in)}</td>
                    <td className="px-3 py-2 text-right text-rose-700">{formatVND(m.total_out)}</td>
                    <td className="px-3 py-2 text-right font-medium">{formatVND(m.closing)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 font-semibold border-t-2 border-slate-300">
                <tr>
                  <td className="px-3 py-2">Tổng</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.opening_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.in_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.out_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.closing_total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
