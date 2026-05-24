import { useCallback, useEffect, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import DateRangePicker, {
  defaultRangeLast30,
  type DateRange,
} from '../../components/DateRangePicker';
import * as reportApi from '../../api/report';
import type { RevenueResponse, RevenueGroupBy } from '../../api/report';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

export default function RevenuePage() {
  const [range, setRange] = useState<DateRange>(() => defaultRangeLast30());
  const [groupBy, setGroupBy] = useState<RevenueGroupBy>('day');
  const [data, setData] = useState<RevenueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(
    async (r: DateRange, gb: RevenueGroupBy) => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getRevenue({
          from: r.from,
          to: r.to,
          group_by: gb,
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
    void fetchData(range, groupBy);
    // initial mount only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = () => {
    if (range.from && range.to && range.from > range.to) return;
    void fetchData(range, groupBy);
  };

  const chartData = (data?.series ?? []).map((p) => ({
    period: p.period,
    revenue: Number(p.revenue),
    profit: Number(p.profit),
  }));

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Báo cáo doanh thu</h1>

      <div className="flex flex-wrap items-end gap-3">
        <DateRangePicker value={range} onChange={setRange} />
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Nhóm theo</span>
          <select
            aria-label="Nhóm theo"
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as RevenueGroupBy)}
            className="border border-slate-300 rounded px-2 py-1"
          >
            <option value="day">Ngày</option>
            <option value="month">Tháng</option>
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

      {data && (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
          <div className="rounded border border-slate-200 bg-white p-4">
            <div className="text-sm text-slate-500">Tổng doanh thu</div>
            <div className="mt-1 text-xl font-semibold">
              {formatVND(data.total_revenue)}
            </div>
          </div>
          <div className="rounded border border-slate-200 bg-white p-4">
            <div className="text-sm text-slate-500">Tổng lợi nhuận</div>
            <div className="mt-1 text-xl font-semibold">
              {formatVND(data.total_profit)}
            </div>
          </div>
          <div className="rounded border border-slate-200 bg-white p-4">
            <div className="text-sm text-slate-500">Số hóa đơn</div>
            <div className="mt-1 text-xl font-semibold">
              {data.total_invoices}
            </div>
          </div>
        </div>
      )}

      <div
        data-testid="revenue-chart"
        className="rounded border border-slate-200 bg-white p-4 overflow-x-auto"
      >
        {loading ? (
          <SkeletonCard />
        ) : chartData.length === 0 ? (
          <EmptyState
            title="Không có dữ liệu"
            description="Không có dữ liệu trong khoảng thời gian này"
          />
        ) : (
          <LineChart width={700} height={300} data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" />
            <YAxis />
            <Tooltip formatter={(v) => formatVND(Number(v ?? 0))} />
            <Line
              type="monotone"
              dataKey="revenue"
              stroke="#0f172a"
              name="Doanh thu"
            />
            <Line
              type="monotone"
              dataKey="profit"
              stroke="#16a34a"
              name="Lợi nhuận"
            />
          </LineChart>
        )}
      </div>
    </div>
  );
}
