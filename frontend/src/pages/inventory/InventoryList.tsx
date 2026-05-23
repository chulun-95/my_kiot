import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { InventoryItem, Pagination } from '../../api/inventory';
import { formatVND, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';

function isLowStock(item: InventoryItem): boolean {
  if (item.min_stock <= 0) return false;
  const qty = Number(item.quantity);
  return Number.isFinite(qty) && qty <= item.min_stock;
}

export default function InventoryList() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [search, setSearch] = useState('');
  const [onlyWithStock, setOnlyWithStock] = useState(false);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await inventoryApi.list({
        page,
        limit: 20,
        search: search || undefined,
        only_with_stock: onlyWithStock,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, search, onlyWithStock]);

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Tồn kho</h1>
        <Link
          to="/inventory/low-stock"
          className="px-3 py-2 rounded border border-slate-300 text-sm"
        >
          Xem hàng sắp hết
        </Link>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="search"
          placeholder="Tìm theo tên hoặc SKU..."
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="px-3 py-2 border border-slate-300 rounded flex-1 min-w-[240px]"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={onlyWithStock}
            onChange={(e) => {
              setPage(1);
              setOnlyWithStock(e.target.checked);
            }}
          />
          Chỉ hiện hàng còn tồn
        </label>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên SP</th>
              <th className="px-3 py-2 text-left">ĐVT</th>
              <th className="px-3 py-2 text-right">Tồn</th>
              <th className="px-3 py-2 text-right">Tồn min</th>
              <th className="px-3 py-2 text-right">Giá vốn</th>
              <th className="px-3 py-2 text-right">Giá bán</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6">
                  <SkeletonRow count={5} />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6">
                  <EmptyState
                    title="Chưa có dữ liệu tồn kho"
                    description="Tồn kho sẽ xuất hiện sau khi nhập hàng hoặc bán hàng."
                  />
                </td>
              </tr>
            ) : (
              items.map((it) => (
                <tr key={it.product_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{it.product_sku}</td>
                  <td className="px-3 py-2">{it.product_name}</td>
                  <td className="px-3 py-2">{it.unit}</td>
                  <td className="px-3 py-2 text-right">
                    <span className="font-medium">{formatQty(it.quantity as number)}</span>
                    {isLowStock(it) && (
                      <span className="ml-2 px-1.5 py-0.5 text-xs rounded bg-amber-100 text-amber-700">
                        Sắp hết
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">{it.min_stock}</td>
                  <td className="px-3 py-2 text-right">{formatVND(it.cost_price as number)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(it.sale_price as number)}</td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      to={`/inventory/${it.product_id}/movements`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block text-xs"
                    >
                      Thẻ kho
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          Trang {pagination.page} / {Math.max(1, pagination.total_pages)} —{' '}
          {pagination.total} mặt hàng
        </span>
        <div className="space-x-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Trước
          </button>
          <button
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
