import { useCallback, useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import DateRangePicker, {
  defaultRangeLast30,
  type DateRange,
} from '../../components/DateRangePicker';
import * as reportApi from '../../api/report';
import type { TopProductsResponse } from '../../api/report';
import { formatVND, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

const LIMIT_OPTIONS = [5, 10, 20, 50];

export default function TopProductsPage() {
  const [range, setRange] = useState<DateRange>(() => defaultRangeLast30());
  const [limit, setLimit] = useState<number>(10);
  const [data, setData] = useState<TopProductsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(
    async (r: DateRange, lim: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getTopProducts({
          from: r.from,
          to: r.to,
          limit: lim,
        });
        setData(res);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void fetchData(range, limit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = () => {
    if (range.from && range.to && range.from > range.to) return;
    void fetchData(range, limit);
  };

  const chartData = (data?.items ?? []).map((it) => ({
    name: it.product_name,
    revenue: Number(it.revenue),
  }));

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Top sản phẩm bán chạy</h1>

      <div className="flex flex-wrap items-end gap-3">
        <DateRangePicker value={range} onChange={setRange} />
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Số lượng</span>
          <select
            aria-label="Số lượng"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="border border-slate-300 rounded px-2 py-1"
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
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

      <div
        data-testid="top-products-chart"
        className="rounded border border-slate-200 bg-white p-4 overflow-x-auto"
      >
        {loading ? (
          <SkeletonCard />
        ) : chartData.length === 0 ? (
          <EmptyState title="Chưa có dữ liệu" />
        ) : (
          <BarChart width={700} height={300} data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(v) => formatVND(Number(v ?? 0))} />
            <Bar dataKey="revenue" fill="#0f172a" name="Doanh thu" />
          </BarChart>
        )}
      </div>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên sản phẩm</th>
              <th className="px-3 py-2 text-right">SL bán</th>
              <th className="px-3 py-2 text-right">Doanh thu</th>
              <th className="px-3 py-2 text-right">Lợi nhuận</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6">
                  <EmptyState title="Chưa có dữ liệu" />
                </td>
              </tr>
            ) : (
              data!.items.map((it) => (
                <tr key={it.product_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">
                    {it.product_sku}
                  </td>
                  <td className="px-3 py-2">{it.product_name}</td>
                  <td className="px-3 py-2 text-right">
                    {formatQty(it.quantity_sold as number)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(it.revenue)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(it.profit)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
