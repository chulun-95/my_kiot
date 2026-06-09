import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as goodsReceiptApi from '../../api/goodsReceipt';
import {
  RECEIPT_PAYMENT_METHOD_LABELS,
  type ReceiptPaymentMethod,
} from '../../api/goodsReceipt';
import * as supplierApi from '../../api/supplier';
import type { SupplierResponse } from '../../api/supplier';
import ProductPicker from '../../components/ProductPicker';
import type { ProductBrief } from '../../api/product';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import MoneyInput from '../../components/MoneyInput';
import QtyInput from '../../components/QtyInput';

interface LineItem {
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string;
  quantity: number;
  cost_price: number;
}

export default function GoodsReceiptForm() {
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<SupplierResponse[]>([]);
  const [supplierId, setSupplierId] = useState<number | ''>('');
  const [lines, setLines] = useState<LineItem[]>([]);
  const [paidAmount, setPaidAmount] = useState<number>(0);
  const [payFull, setPayFull] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<ReceiptPaymentMethod>('CASH');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await supplierApi.listSuppliers({ limit: 100 });
        setSuppliers(res.items);
      } catch {
        // optional
      }
    })();
  }, []);

  const total = useMemo(
    () => lines.reduce((s, l) => s + l.quantity * l.cost_price, 0),
    [lines],
  );

  useEffect(() => {
    if (payFull) setPaidAmount(total);
  }, [payFull, total]);

  const onPick = (p: ProductBrief) => {
    setLines((prev) => {
      const idx = prev.findIndex((l) => l.product_id === p.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], quantity: next[idx].quantity + 1 };
        return next;
      }
      return [
        ...prev,
        {
          product_id: p.id,
          product_name: p.name,
          product_sku: p.sku,
          unit: p.unit,
          quantity: 1,
          cost_price: Number(p.cost_price ?? 0),
        },
      ];
    });
  };

  const updateLine = (idx: number, patch: Partial<LineItem>) => {
    setLines((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  };

  const removeLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const onSubmit = async () => {
    setError(null);
    if (lines.length === 0) {
      setError('Vui lòng thêm ít nhất 1 sản phẩm');
      return;
    }
    for (const l of lines) {
      if (l.quantity <= 0) {
        setError(`Số lượng của ${l.product_name} phải > 0`);
        return;
      }
      if (l.cost_price < 0) {
        setError(`Giá nhập của ${l.product_name} không hợp lệ`);
        return;
      }
    }
    setSubmitting(true);
    try {
      const res = await goodsReceiptApi.create({
        supplier_id: supplierId === '' ? null : supplierId,
        items: lines.map((l) => ({
          product_id: l.product_id,
          quantity: l.quantity,
          cost_price: l.cost_price,
        })),
        paid_amount: paidAmount || 0,
        payment_method: paymentMethod,
        note: note || null,
      });
      navigate(`/goods-receipts/${res.id}`);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Nhập hàng mới</h1>

      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div>
          <label className="block text-sm text-slate-600 mb-1">Nhà cung cấp</label>
          <select
            value={supplierId}
            onChange={(e) =>
              setSupplierId(e.target.value === '' ? '' : Number(e.target.value))
            }
            className="px-3 py-2 border border-slate-300 rounded w-full max-w-md"
          >
            <option value="">-- Không chọn NCC --</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-slate-600 mb-1">
            Thêm sản phẩm
          </label>
          <ProductPicker onPick={onPick} placeholder="Quét mã vạch hoặc tìm SP để thêm vào phiếu nhập..." />
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên SP</th>
              <th className="px-3 py-2 text-left">ĐVT</th>
              <th className="px-3 py-2 text-right">Số lượng</th>
              <th className="px-3 py-2 text-right">Giá nhập</th>
              <th className="px-3 py-2 text-right">Thành tiền</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Chưa có sản phẩm trong phiếu
                </td>
              </tr>
            ) : (
              lines.map((l, idx) => (
                <tr key={`${l.product_id}-${idx}`} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{l.product_sku}</td>
                  <td className="px-3 py-2">{l.product_name}</td>
                  <td className="px-3 py-2">{l.unit}</td>
                  <td className="px-3 py-2 text-right">
                    <QtyInput
                      value={l.quantity}
                      onChange={(v) => updateLine(idx, { quantity: v })}
                      className="w-24 px-2 py-1 border border-slate-300 rounded text-right"
                      aria-label={`Số lượng ${l.product_name}`}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="w-36 inline-block">
                      <MoneyInput
                        value={l.cost_price}
                        onChange={(v) => updateLine(idx, { cost_price: v })}
                        className="w-full px-2 py-1 border border-slate-300 rounded"
                        aria-label={`Giá nhập ${l.product_name}`}
                      />
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(l.quantity * l.cost_price)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => removeLine(idx)}
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

      <div className="bg-white border border-slate-200 rounded p-4 space-y-3 max-w-md ml-auto">
        <div className="flex items-center justify-between">
          <span className="text-slate-600">Tổng tiền</span>
          <span className="font-semibold text-lg">{formatVND(total)}</span>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="gr-paid-amount" className="text-sm text-slate-600">
              Đã thanh toán
            </label>
            <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={payFull}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setPayFull(checked);
                  if (checked) setPaidAmount(total);
                }}
                className="h-4 w-4"
              />
              Thanh toán đủ
            </label>
          </div>
          <MoneyInput
            id="gr-paid-amount"
            value={paidAmount}
            onChange={(v) => {
              setPaidAmount(v);
              if (payFull && v !== total) setPayFull(false);
            }}
            className={`w-full px-3 py-2 border border-slate-300 rounded ${payFull ? 'bg-slate-50 text-slate-500' : ''}`}
            aria-label="Đã thanh toán"
            disabled={payFull}
          />
        </div>
        {paidAmount > 0 && (
          <div>
            <label htmlFor="gr-payment-method" className="block text-sm text-slate-600 mb-1">
              Phương thức thanh toán
            </label>
            <select
              id="gr-payment-method"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value as ReceiptPaymentMethod)}
              className="w-full px-3 py-2 border border-slate-300 rounded"
              aria-label="Phương thức thanh toán"
            >
              {Object.entries(RECEIPT_PAYMENT_METHOD_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="block text-sm text-slate-600 mb-1">Ghi chú</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-slate-300 rounded"
          />
        </div>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => navigate('/goods-receipts')}
          className="px-3 py-2 rounded border border-slate-300"
        >
          Hủy
        </button>
        <button
          onClick={onSubmit}
          disabled={submitting}
          className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Lưu phiếu nháp'}
        </button>
      </div>
    </div>
  );
}
