import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { LowStockItem } from '../../api/inventory';
import { formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function LowStock() {
  const [items, setItems] = useState<LowStockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await inventoryApi.getLowStock();
        setItems(res.items);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Hàng sắp hết</h1>
        <Link to="/inventory" className="text-sm text-slate-600 hover:underline">
          ← Tồn kho
        </Link>
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
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Không có sản phẩm nào sắp hết hàng.
                </td>
              </tr>
            ) : (
              items.map((it) => (
                <tr key={it.product_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{it.product_sku}</td>
                  <td className="px-3 py-2">{it.product_name}</td>
                  <td className="px-3 py-2">{it.unit}</td>
                  <td className="px-3 py-2 text-right text-amber-700 font-medium">
                    {formatQty(it.quantity as number)}
                  </td>
                  <td className="px-3 py-2 text-right">{it.min_stock}</td>
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
    </div>
  );
}
