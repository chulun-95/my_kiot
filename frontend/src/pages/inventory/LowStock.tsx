import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { LowStockItem, LowStockSummary } from '../../api/inventory';
import { formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';

type Section = {
  title: string;
  description: string;
  tone: 'critical' | 'warn';
  items: LowStockItem[];
};

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'critical' | 'warn' | 'neutral';
}) {
  const palette =
    tone === 'critical'
      ? 'border-rose-300 bg-rose-50 text-rose-700'
      : tone === 'warn'
        ? 'border-amber-300 bg-amber-50 text-amber-700'
        : 'border-slate-200 bg-white text-slate-700';
  return (
    <div className={`rounded-lg border px-4 py-3 ${palette}`}>
      <div className="text-xs uppercase tracking-wide">{label}</div>
      <div className="mt-1 text-3xl font-semibold">{value}</div>
    </div>
  );
}

function SectionTable({ section }: { section: Section }) {
  const isCritical = section.tone === 'critical';
  const headerColor = isCritical
    ? 'bg-rose-50 text-rose-800 border-rose-200'
    : 'bg-amber-50 text-amber-800 border-amber-200';
  const badgeColor = isCritical
    ? 'bg-rose-600 text-white'
    : 'bg-amber-500 text-white';
  return (
    <section className="space-y-2">
      <div className={`flex items-center justify-between px-3 py-2 rounded-t border ${headerColor}`}>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center justify-center min-w-[1.75rem] h-7 px-2 rounded-full text-xs font-semibold ${badgeColor}`}
          >
            {section.items.length}
          </span>
          <div>
            <h2 className="text-base font-semibold">{section.title}</h2>
            <p className="text-xs opacity-80">{section.description}</p>
          </div>
        </div>
      </div>
      <div className="bg-white border border-t-0 border-slate-200 rounded-b overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên SP</th>
              <th className="px-3 py-2 text-left">ĐVT</th>
              <th className="px-3 py-2 text-right">Tồn hiện tại</th>
              <th className="px-3 py-2 text-right">Tồn min</th>
              <th className="px-3 py-2 text-right">Cần nhập tối thiểu</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {section.items.map((it) => {
              const qty = Number(it.quantity);
              const shortage = Number(it.shortage);
              return (
                <tr key={it.product_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{it.product_sku}</td>
                  <td className="px-3 py-2">{it.product_name}</td>
                  <td className="px-3 py-2">{it.unit}</td>
                  <td
                    className={`px-3 py-2 text-right font-semibold ${
                      isCritical ? 'text-rose-700' : 'text-amber-700'
                    }`}
                  >
                    {formatQty(qty)}
                  </td>
                  <td className="px-3 py-2 text-right">{it.min_stock}</td>
                  <td className="px-3 py-2 text-right font-medium">
                    {formatQty(shortage)} {it.unit}
                  </td>
                  <td className="px-3 py-2 text-right space-x-1">
                    <Link
                      to={`/inventory/${it.product_id}/movements`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block text-xs"
                    >
                      Thẻ kho
                    </Link>
                    <Link
                      to="/goods-receipts/new"
                      className="px-2 py-1 rounded bg-slate-900 text-white inline-block text-xs"
                    >
                      Nhập hàng
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function LowStock() {
  const [items, setItems] = useState<LowStockItem[]>([]);
  const [summary, setSummary] = useState<LowStockSummary>({
    out_of_stock_count: 0,
    low_count: 0,
    total_count: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await inventoryApi.getLowStock();
        setItems(res.items);
        setSummary(res.summary);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const sections = useMemo<Section[]>(() => {
    const outItems = items.filter((i) => i.severity === 'OUT_OF_STOCK');
    const lowItems = items.filter((i) => i.severity === 'LOW');
    const result: Section[] = [];
    if (outItems.length > 0) {
      result.push({
        title: 'Đã hết hàng — cần nhập gấp',
        description: 'Tồn kho ≤ 0. Không bán được, mất doanh thu nếu khách hỏi.',
        tone: 'critical',
        items: outItems,
      });
    }
    if (lowItems.length > 0) {
      result.push({
        title: 'Sắp hết — đặt hàng sớm',
        description: 'Tồn còn dưới hoặc bằng định mức tối thiểu.',
        tone: 'warn',
        items: lowItems,
      });
    }
    return result;
  }, [items]);

  const isEmpty = !loading && items.length === 0 && !error;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Cảnh báo tồn kho</h1>
          <p className="text-sm text-slate-500">
            Trang dành cho chủ shop — kiểm tra hàng cần đặt thêm hoặc đã hết.
          </p>
        </div>
        <Link to="/inventory" className="text-sm text-slate-600 hover:underline">
          ← Tồn kho
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700"
        >
          {error}
        </div>
      )}

      {summary.out_of_stock_count > 0 && (
        <div
          role="alert"
          className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-3 text-rose-800"
        >
          <div className="font-semibold">
            ⚠ Có {summary.out_of_stock_count} sản phẩm đã hết hàng
          </div>
          <div className="text-sm">
            Khách đang hỏi mà không có hàng — đặt nhập càng sớm càng tốt.
          </div>
        </div>
      )}

      <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
        <SummaryCard
          label="Đã hết hàng"
          value={summary.out_of_stock_count}
          tone={summary.out_of_stock_count > 0 ? 'critical' : 'neutral'}
        />
        <SummaryCard
          label="Sắp hết"
          value={summary.low_count}
          tone={summary.low_count > 0 ? 'warn' : 'neutral'}
        />
        <SummaryCard label="Tổng số cảnh báo" value={summary.total_count} tone="neutral" />
      </div>

      {loading && (
        <div className="bg-white border border-slate-200 rounded p-4">
          <SkeletonRow count={5} />
        </div>
      )}

      {isEmpty && (
        <EmptyState
          title="Không có sản phẩm sắp hết"
          description="Tất cả SP đang trên ngưỡng tồn tối thiểu — kho ổn định."
        />
      )}

      {sections.map((s) => (
        <SectionTable key={s.title} section={s} />
      ))}
    </div>
  );
}
