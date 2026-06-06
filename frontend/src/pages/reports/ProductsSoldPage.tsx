import { useCallback, useEffect, useState } from 'react';
import dayjs from 'dayjs';
import DateRangePicker, {
  type DateRange,
} from '../../components/DateRangePicker';
import * as reportApi from '../../api/report';
import type {
  ProductsSoldResponse,
  ProductsSoldSortBy,
  SortOrder,
} from '../../api/report';
import { listCategories, type CategoryNode } from '../../api/category';
import { formatVND, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

interface CatOption {
  id: number;
  label: string;
}

function flatten(nodes: CategoryNode[], depth = 0): CatOption[] {
  const out: CatOption[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, label: `${'— '.repeat(depth)}${n.name}` });
    if (n.children?.length) out.push(...flatten(n.children, depth + 1));
  }
  return out;
}

const SORT_OPTIONS: { value: ProductsSoldSortBy; label: string }[] = [
  { value: 'revenue', label: 'Doanh thu thuần' },
  { value: 'quantity', label: 'Số lượng bán' },
  { value: 'profit', label: 'Lợi nhuận gộp' },
];

export default function ProductsSoldPage() {
  const [range, setRange] = useState<DateRange>(() => {
    const today = dayjs().format('YYYY-MM-DD');
    return { from: today, to: today };
  });
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [sortBy, setSortBy] = useState<ProductsSoldSortBy>('revenue');
  const [order, setOrder] = useState<SortOrder>('desc');
  const [page, setPage] = useState(1);
  const [cats, setCats] = useState<CatOption[]>([]);
  const [data, setData] = useState<ProductsSoldResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listCategories()
      .then((res) => setCats(flatten(res.items)))
      .catch(() => setCats([]));
  }, []);

  const fetchData = useCallback(
    async (
      r: DateRange,
      cat: number | '',
      sb: ProductsSoldSortBy,
      ord: SortOrder,
      pg: number,
    ) => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getProductsSold({
          from: r.from,
          to: r.to,
          ...(cat ? { category_id: cat } : {}),
          sort_by: sb,
          order: ord,
          page: pg,
          limit: 20,
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
    void fetchData(range, categoryId, sortBy, order, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, order, page]);

  const onSubmit = () => {
    if (range.from && range.to && range.from > range.to) return;
    setPage(1);
    void fetchData(range, categoryId, sortBy, order, 1);
  };

  const toggleSort = (col: ProductsSoldSortBy) => {
    if (sortBy === col) {
      setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(col);
      setOrder('desc');
    }
    setPage(1);
  };

  const sortArrow = (col: ProductsSoldSortBy) =>
    sortBy === col ? (order === 'desc' ? ' ▼' : ' ▲') : '';

  const items = data?.items ?? [];
  const totals = data?.totals;
  const pag = data?.pagination;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Sản phẩm đã bán</h1>

      <div className="flex flex-wrap items-end gap-3">
        <DateRangePicker value={range} onChange={setRange} />
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Nhóm hàng</span>
          <select
            aria-label="Nhóm hàng"
            value={categoryId}
            onChange={(e) =>
              setCategoryId(e.target.value ? Number(e.target.value) : '')
            }
            className="border border-slate-300 rounded px-2 py-1"
          >
            <option value="">Tất cả nhóm hàng</option>
            {cats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Sắp xếp theo</span>
          <select
            aria-label="Sắp xếp theo"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as ProductsSoldSortBy);
              setPage(1);
            }}
            className="border border-slate-300 rounded px-2 py-1"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
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

      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        {loading ? (
          <div className="p-4">
            <SkeletonCard />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">SKU</th>
                <th className="px-3 py-2 text-left">Tên sản phẩm</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('quantity')}
                >
                  SL bán{sortArrow('quantity')}
                </th>
                <th className="px-3 py-2 text-right">Doanh thu</th>
                <th className="px-3 py-2 text-right">Giảm giá</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('revenue')}
                >
                  Doanh thu thuần{sortArrow('revenue')}
                </th>
                <th className="px-3 py-2 text-right">Giá vốn</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('profit')}
                >
                  Lợi nhuận gộp{sortArrow('profit')}
                </th>
                <th className="px-3 py-2 text-right">Tỷ suất %</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-6">
                    <EmptyState title="Không có sản phẩm nào bán ra trong kỳ" />
                  </td>
                </tr>
              ) : (
                items.map((it) => (
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
                      {formatVND(it.discount)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.net_revenue)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.cost)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.profit)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {Number(it.margin_pct).toFixed(1)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            {totals && items.length > 0 && (
              <tfoot className="bg-slate-50 font-semibold border-t-2 border-slate-300">
                <tr>
                  <td className="px-3 py-2" colSpan={2}>
                    Tổng cộng
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatQty(totals.quantity_sold as number)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.revenue)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.discount)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.net_revenue)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.cost)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.profit)}
                  </td>
                  <td className="px-3 py-2" />
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </div>

      {pag && pag.total_pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            Trước
          </button>
          <span>
            Trang {pag.page}/{pag.total_pages}
          </span>
          <button
            disabled={page >= pag.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            Sau
          </button>
        </div>
      )}
    </div>
  );
}
