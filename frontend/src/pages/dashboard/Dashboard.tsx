import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as reportApi from '../../api/report';
import type { DashboardResponse } from '../../api/report';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

interface CardProps {
  label: string;
  value: string;
  to?: string;
  accent?: string;
}

function Card({ label, value, to, accent }: CardProps) {
  const inner = (
    <div
      className={`rounded-lg border bg-white p-4 shadow-sm ${accent ?? 'border-slate-200'}`}
    >
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
  if (to) {
    return (
      <Link to={to} className="block hover:opacity-90">
        {inner}
      </Link>
    );
  }
  return inner;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getDashboard();
        if (!cancelled) setData(res);
      } catch (err) {
        if (!cancelled) setError(toFriendlyMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Tổng quan</h1>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="text-rose-600">
        {error}
      </div>
    );
  }
  if (!data) {
    return <EmptyState title="Chưa có dữ liệu" />;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Tổng quan</h1>
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Doanh thu hôm nay" value={formatVND(data.today_revenue)} />
        <Card label="Số hóa đơn hôm nay" value={String(data.today_invoices)} />
        <Card label="Lợi nhuận hôm nay" value={formatVND(data.today_profit)} />
        <Card label="Khách hôm nay" value={String(data.today_customers)} />
        <Card label="Hóa đơn nháp" value={String(data.pending_drafts)} />
        <Card
          label="Hàng sắp hết"
          value={String(data.low_stock_count)}
          to="/inventory/low-stock"
          accent={data.low_stock_count > 0 ? 'border-amber-300' : undefined}
        />
        <Card label="Giá trị tồn kho" value={formatVND(data.inventory_value)} />
      </div>
    </div>
  );
}
