import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as reportApi from '../../api/report';
import type { StockSummaryResponse } from '../../api/report';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

interface TileProps {
  label: string;
  value: string;
  to?: string;
  accent?: string;
}

function Tile({ label, value, to, accent }: TileProps) {
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

export default function StockSummaryPage() {
  const [data, setData] = useState<StockSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getStockSummary();
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
        <h1 className="text-2xl font-semibold">Tổng quan tồn kho</h1>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
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
      <h1 className="text-2xl font-semibold">Tổng quan tồn kho</h1>
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
        <Tile label="Tổng số sản phẩm" value={String(data.total_products)} />
        <Tile
          label="SP còn hàng"
          value={String(data.products_in_stock)}
          accent="border-emerald-300"
        />
        <Tile
          label="SP hết hàng"
          value={String(data.products_out_of_stock)}
          accent="border-rose-300"
        />
        <Tile
          label="SP sắp hết"
          value={String(data.low_stock_count)}
          to="/inventory/low-stock"
          accent={data.low_stock_count > 0 ? 'border-amber-300' : undefined}
        />
        <Tile
          label="Giá trị tồn kho"
          value={formatVND(data.total_inventory_value)}
        />
        <Tile label="Cập nhật" value={formatDate(data.last_updated)} />
      </div>
    </div>
  );
}
