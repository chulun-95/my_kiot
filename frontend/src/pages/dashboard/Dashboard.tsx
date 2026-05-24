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

  const outCount = data.out_of_stock_count ?? 0;
  const lowOnlyCount = Math.max(0, data.low_stock_count - outCount);
  const hasLowStockAlert = data.low_stock_count > 0;
  const cardAccent =
    outCount > 0
      ? 'border-rose-300 bg-rose-50'
      : lowOnlyCount > 0
        ? 'border-amber-300 bg-amber-50'
        : undefined;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Tổng quan</h1>

      {hasLowStockAlert && (
        <Link
          to="/inventory/low-stock"
          role="alert"
          className={`block rounded-lg border-2 px-4 py-3 transition hover:shadow-sm ${
            outCount > 0
              ? 'border-rose-400 bg-rose-50 text-rose-800'
              : 'border-amber-400 bg-amber-50 text-amber-800'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-semibold">
                {outCount > 0
                  ? `⚠ ${outCount} sản phẩm đã hết hàng${
                      lowOnlyCount > 0 ? `, ${lowOnlyCount} sản phẩm sắp hết` : ''
                    }`
                  : `${lowOnlyCount} sản phẩm sắp hết tồn`}
              </div>
              <div className="text-sm opacity-90">
                {outCount > 0
                  ? 'Cần đặt nhập gấp để không mất doanh thu khi khách hỏi.'
                  : 'Đặt thêm hàng sớm để tránh đứt nguồn bán.'}
              </div>
            </div>
            <span className="text-sm underline whitespace-nowrap">
              Xem chi tiết →
            </span>
          </div>
        </Link>
      )}

      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Doanh thu hôm nay" value={formatVND(data.today_revenue)} />
        <Card label="Số hóa đơn hôm nay" value={String(data.today_invoices)} />
        <Card label="Lợi nhuận hôm nay" value={formatVND(data.today_profit)} />
        <Card label="Khách hôm nay" value={String(data.today_customers)} />
        <Card label="Hóa đơn nháp" value={String(data.pending_drafts)} />
        <Card
          label={outCount > 0 ? 'Hàng hết / sắp hết' : 'Hàng sắp hết'}
          value={
            outCount > 0
              ? `${outCount} hết · ${lowOnlyCount} sắp hết`
              : String(data.low_stock_count)
          }
          to="/inventory/low-stock"
          accent={cardAccent}
        />
        <Card label="Giá trị tồn kho" value={formatVND(data.inventory_value)} />
      </div>
    </div>
  );
}
