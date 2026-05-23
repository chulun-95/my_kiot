import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as productApi from '../../api/product';
import * as categoryApi from '../../api/category';
import type {
  Pagination,
  ProductResponse,
  ProductStatus,
} from '../../api/product';
import type { CategoryNode } from '../../api/category';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';

function flattenCategories(nodes: CategoryNode[], depth = 0): Array<{ id: number; label: string }> {
  const out: Array<{ id: number; label: string }> = [];
  for (const n of nodes) {
    out.push({ id: n.id, label: `${'— '.repeat(depth)}${n.name}` });
    if (n.children?.length) out.push(...flattenCategories(n.children, depth + 1));
  }
  return out;
}

export default function ProductList() {
  const [items, setItems] = useState<ProductResponse[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<ProductStatus | ''>('');
  const [categories, setCategories] = useState<Array<{ id: number; label: string }>>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await categoryApi.listCategories();
        setCategories(flattenCategories(res.items));
      } catch {
        // ignore — filter is optional
      }
    })();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await productApi.listProducts({
        page,
        limit: 20,
        search: search || undefined,
        category_id: categoryId === '' ? undefined : categoryId,
        status: statusFilter === '' ? undefined : statusFilter,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryId, statusFilter]);

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sản phẩm</h1>
        <Link
          to="/products/new"
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Thêm sản phẩm
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          type="search"
          placeholder="Tìm theo tên, SKU hoặc mã vạch..."
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="px-3 py-2 border border-slate-300 rounded flex-1 min-w-[240px]"
        />
        <select
          value={categoryId}
          onChange={(e) => {
            setPage(1);
            setCategoryId(e.target.value === '' ? '' : Number(e.target.value));
          }}
          className="px-3 py-2 border border-slate-300 rounded"
        >
          <option value="">Tất cả nhóm</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setPage(1);
            setStatusFilter(e.target.value as ProductStatus | '');
          }}
          className="px-3 py-2 border border-slate-300 rounded"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="ACTIVE">Đang bán</option>
          <option value="INACTIVE">Ngừng bán</option>
          <option value="DRAFT">Nháp</option>
        </select>
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
              <th className="px-3 py-2 text-left">Tên</th>
              <th className="px-3 py-2 text-left">Nhóm</th>
              <th className="px-3 py-2 text-left">Đơn vị</th>
              <th className="px-3 py-2 text-right">Giá bán</th>
              <th className="px-3 py-2 text-right">Tồn min</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
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
                    title="Chưa có sản phẩm"
                    description="Bấm 'Thêm sản phẩm' để bắt đầu nhập danh mục."
                  />
                </td>
              </tr>
            ) : (
              items.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{p.sku}</td>
                  <td className="px-3 py-2">{p.name}</td>
                  <td className="px-3 py-2">{p.category_name ?? '-'}</td>
                  <td className="px-3 py-2">{p.unit}</td>
                  <td className="px-3 py-2 text-right">{formatVND(p.sale_price as number)}</td>
                  <td className="px-3 py-2 text-right">{p.min_stock}</td>
                  <td className="px-3 py-2">
                    {p.status === 'ACTIVE' ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                        Đang bán
                      </span>
                    ) : p.status === 'INACTIVE' ? (
                      <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                        Ngừng bán
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                        Nháp
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    <Link
                      to={`/products/${p.id}`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block"
                    >
                      Xem
                    </Link>
                    <Link
                      to={`/products/${p.id}/edit`}
                      className="px-2 py-1 rounded border border-slate-300 inline-block"
                    >
                      Sửa
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
          {pagination.total} sản phẩm
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
