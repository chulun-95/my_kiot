import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as inventoryApi from '../../api/inventory';
import type { AdjustmentResultItem } from '../../api/inventory';
import ProductPicker from '../../components/ProductPicker';
import type { ProductBrief } from '../../api/product';
import { formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

interface Row {
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string;
  current_quantity: number;
  new_quantity: number;
  reason: string;
}

export default function AdjustmentForm() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Row[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AdjustmentResultItem[] | null>(null);

  const onPick = async (p: ProductBrief) => {
    if (rows.some((r) => r.product_id === p.id)) return;
    let current = 0;
    try {
      const res = await inventoryApi.list({ search: p.sku, limit: 1 });
      const match = res.items.find((i) => i.product_id === p.id);
      if (match) current = Number(match.quantity);
    } catch {
      // ignore — default to 0
    }
    setRows((prev) => [
      ...prev,
      {
        product_id: p.id,
        product_name: p.name,
        product_sku: p.sku,
        unit: p.unit,
        current_quantity: current,
        new_quantity: current,
        reason: '',
      },
    ]);
  };

  const updateRow = (idx: number, patch: Partial<Row>) => {
    setRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  };

  const removeRow = (idx: number) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  };

  const onSubmit = async () => {
    setError(null);
    if (rows.length === 0) {
      setError('Vui lòng thêm ít nhất 1 sản phẩm');
      return;
    }
    for (const r of rows) {
      if (!Number.isFinite(r.new_quantity) || r.new_quantity < 0) {
        setError(`Số lượng mới của ${r.product_name} không hợp lệ`);
        return;
      }
    }
    setSubmitting(true);
    try {
      const res = await inventoryApi.createAdjustment({
        items: rows.map((r) => ({
          product_id: r.product_id,
          new_quantity: r.new_quantity,
          reason: r.reason || null,
        })),
      });
      setResults(res.items);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (results) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h1 className="text-2xl font-semibold">Kết quả điều chỉnh</h1>
        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Sản phẩm</th>
                <th className="px-3 py-2 text-right">Tồn cũ</th>
                <th className="px-3 py-2 text-right">Tồn mới</th>
                <th className="px-3 py-2 text-right">Thay đổi</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const delta = Number(r.delta);
                return (
                  <tr key={r.product_id} className="border-t border-slate-100">
                    <td className="px-3 py-2">
                      <span className="font-medium">{r.product_name}</span>
                      <span className="ml-2 text-xs font-mono text-slate-500">{r.product_sku}</span>
                    </td>
                    <td className="px-3 py-2 text-right">{formatQty(r.old_quantity as number)}</td>
                    <td className="px-3 py-2 text-right">{formatQty(r.new_quantity as number)}</td>
                    <td
                      className={`px-3 py-2 text-right font-medium ${
                        delta >= 0 ? 'text-emerald-700' : 'text-rose-700'
                      }`}
                    >
                      {delta >= 0 ? '+' : ''}
                      {formatQty(delta)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <button
          onClick={() => navigate('/inventory/adjustments')}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          Quay về danh sách
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <h1 className="text-2xl font-semibold">Điều chỉnh tồn kho</h1>

      <div className="bg-white border border-slate-200 rounded p-4">
        <label className="block text-sm text-slate-600 mb-1">Thêm sản phẩm</label>
        <ProductPicker onPick={onPick} placeholder="Tìm sản phẩm để thêm vào phiếu điều chỉnh..." />
      </div>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên SP</th>
              <th className="px-3 py-2 text-left">ĐVT</th>
              <th className="px-3 py-2 text-right">Tồn hiện tại</th>
              <th className="px-3 py-2 text-right">Tồn mới</th>
              <th className="px-3 py-2 text-left">Lý do</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Chưa có sản phẩm
                </td>
              </tr>
            ) : (
              rows.map((r, idx) => (
                <tr key={r.product_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{r.product_sku}</td>
                  <td className="px-3 py-2">{r.product_name}</td>
                  <td className="px-3 py-2">{r.unit}</td>
                  <td className="px-3 py-2 text-right">{formatQty(r.current_quantity)}</td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      value={r.new_quantity}
                      onChange={(e) =>
                        updateRow(idx, { new_quantity: Number(e.target.value) })
                      }
                      className="w-24 px-2 py-1 border border-slate-300 rounded text-right"
                      aria-label={`Tồn mới ${r.product_name}`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={r.reason}
                      onChange={(e) => updateRow(idx, { reason: e.target.value })}
                      placeholder="vd: Kiểm kê tháng"
                      className="w-full px-2 py-1 border border-slate-300 rounded"
                      aria-label={`Lý do ${r.product_name}`}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => removeRow(idx)}
                      className="px-2 py-1 rounded border border-rose-300 text-rose-700 text-xs"
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => navigate('/inventory/adjustments')}
          className="px-3 py-2 rounded border border-slate-300"
        >
          Hủy
        </button>
        <button
          onClick={onSubmit}
          disabled={submitting}
          className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Xác nhận điều chỉnh'}
        </button>
      </div>
    </div>
  );
}
