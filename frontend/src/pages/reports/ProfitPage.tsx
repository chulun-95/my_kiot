import { useCallback, useEffect, useState } from 'react';
import DateRangePicker, {
  defaultRangeLast30,
  type DateRange,
} from '../../components/DateRangePicker';
import * as reportApi from '../../api/report';
import type { ProfitResponse } from '../../api/report';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function ProfitPage() {
  const [range, setRange] = useState<DateRange>(() => defaultRangeLast30());
  const [data, setData] = useState<ProfitResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (r: DateRange) => {
    setLoading(true);
    setError(null);
    try {
      const res = await reportApi.getProfit({ from: r.from, to: r.to });
      setData(res);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData(range);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = () => {
    if (range.from && range.to && range.from > range.to) return;
    void fetchData(range);
  };

  const marginPct = (() => {
    if (!data) return null;
    const rev = Number(data.total_revenue);
    if (!Number.isFinite(rev) || rev === 0) return null;
    const profit = Number(data.gross_profit);
    return (profit / rev) * 100;
  })();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Báo cáo lợi nhuận</h1>

      <div className="flex flex-wrap items-end gap-3">
        <DateRangePicker value={range} onChange={setRange} />
        <button
          onClick={onSubmit}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          Xem báo cáo
        </button>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-slate-500">Đang tải...</div>
      ) : data ? (
        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Từ ngày</td>
                <td className="px-3 py-2 text-right font-medium">
                  {data.from_date}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Đến ngày</td>
                <td className="px-3 py-2 text-right font-medium">
                  {data.to_date}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Tổng doanh thu</td>
                <td className="px-3 py-2 text-right font-medium">
                  {formatVND(data.total_revenue)}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Tổng giá vốn</td>
                <td className="px-3 py-2 text-right font-medium">
                  {formatVND(data.total_cost)}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Lợi nhuận gộp</td>
                <td className="px-3 py-2 text-right font-semibold text-emerald-700">
                  {formatVND(data.gross_profit)}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Biên lợi nhuận</td>
                <td className="px-3 py-2 text-right font-medium">
                  {marginPct === null ? '—' : `${marginPct.toFixed(2)} %`}
                </td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2 text-slate-600">Số hóa đơn</td>
                <td className="px-3 py-2 text-right font-medium">
                  {data.invoices}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
