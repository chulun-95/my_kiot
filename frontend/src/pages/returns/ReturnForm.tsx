import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import * as api from '../../api/salesReturn';
import type { ReturnableLine } from '../../api/salesReturn';
import { formatVND, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

interface FormRow {
  invoice_item_id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string | null;
  sold_quantity: number;
  returnable_quantity: number;
  unit_price: number;
  return_quantity: number;
}

export default function ReturnForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const invoiceId = searchParams.get('invoice');

  const [rows, setRows] = useState<FormRow[]>([]);
  const [refundMethod, setRefundMethod] = useState<'CASH' | 'BANK_TRANSFER' | 'EWALLET'>('CASH');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!invoiceId) {
      setError('Chưa chọn hóa đơn');
      setLoading(false);
      return;
    }
    api
      .getReturnable(Number(invoiceId))
      .then((data) => {
        setRows(
          data.lines.map((line) => ({
            invoice_item_id: line.invoice_item_id,
            product_id: line.product_id,
            product_name: line.product_name,
            product_sku: line.product_sku,
            unit: line.unit,
            sold_quantity: Number(line.sold_quantity),
            returnable_quantity: Number(line.returnable_quantity),
            unit_price: Number(line.unit_price),
            return_quantity: 0,
          })),
        );
      })
      .catch((e) => setError(toFriendlyMessage(e)))
      .finally(() => setLoading(false));
  }, [invoiceId]);

  const updateRow = (idx: number, patch: Partial<FormRow>) => {
    setRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  };

  const totalRefund = rows.reduce((sum, r) => sum + r.return_quantity * r.unit_price, 0);
  const hasItems = rows.some((r) => r.return_quantity > 0);

  const onSubmit = async () => {
    setError(null);
    if (!hasItems) {
      setError('Vui lòng chọn ít nhất 1 sản phẩm để trả');
      return;
    }
    for (const r of rows) {
      if (r.return_quantity > 0 && r.return_quantity > r.returnable_quantity) {
        setError(`Trả vượt số có thể trả của ${r.product_name}`);
        return;
      }
    }
    setSubmitting(true);
    try {
      await api.createReturn({
        invoice_id: Number(invoiceId),
        items: rows
          .filter((r) => r.return_quantity > 0)
          .map((r) => ({
            invoice_item_id: r.invoice_item_id,
            quantity: r.return_quantity,
          })),
        refund_method: refundMethod,
        reason: reason || undefined,
      });
      navigate('/returns');
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-sm text-slate-500">Đang tải...</div>;
  if (error && loading) return <div className="text-sm text-rose-600">{error}</div>;

  return (
    <div className="space-y-4 max-w-5xl">
      <h1 className="text-2xl font-semibold">Trả hàng</h1>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Sản phẩm</th>
              <th className="px-3 py-2 text-right">Đã bán</th>
              <th className="px-3 py-2 text-right">Có thể trả</th>
              <th className="px-3 py-2 text-right">Trả</th>
              <th className="px-3 py-2 text-right">Hoàn tiền</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Không có sản phẩm
                </td>
              </tr>
            ) : (
              rows.map((r, idx) => (
                <tr key={r.invoice_item_id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{r.product_sku}</td>
                  <td className="px-3 py-2">{r.product_name}</td>
                  <td className="px-3 py-2 text-right">{formatQty(r.sold_quantity)}</td>
                  <td className="px-3 py-2 text-right">{formatQty(r.returnable_quantity)}</td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      max={r.returnable_quantity}
                      value={r.return_quantity}
                      onChange={(e) => updateRow(idx, { return_quantity: Number(e.target.value) })}
                      className="w-24 px-2 py-1 border border-slate-300 rounded text-right"
                      aria-label={`Trả ${r.product_name}`}
                      {...viValidity({
                        rangeUnderflow: 'Không được nhỏ hơn 0',
                        rangeOverflow: `Không được vượt quá ${r.returnable_quantity}`,
                        typeMismatch: 'Vui lòng nhập số',
                      })}
                    />
                  </td>
                  <td className="px-3 py-2 text-right text-rose-700">
                    {formatVND(r.return_quantity * r.unit_price)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex justify-between font-semibold text-base">
          <span>Tổng hoàn tiền</span>
          <span className="text-rose-700">{formatVND(totalRefund)}</span>
        </div>

        <div>
          <label className="block text-sm text-slate-600 mb-2">Phương thức hoàn tiền</label>
          <select
            value={refundMethod}
            onChange={(e) => setRefundMethod(e.target.value as 'CASH' | 'BANK_TRANSFER' | 'EWALLET')}
            className="w-full px-3 py-2 border border-slate-300 rounded"
          >
            <option value="CASH">Tiền mặt</option>
            <option value="BANK_TRANSFER">Chuyển khoản</option>
            <option value="EWALLET">Ví điện tử</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-slate-600 mb-2">Lý do trả hàng</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="vd: Sản phẩm lỗi, không đúng mẫu..."
            className="w-full px-3 py-2 border border-slate-300 rounded"
          />
        </div>
      </div>

      {error && !loading && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => navigate('/returns')}
          className="px-3 py-2 rounded border border-slate-300"
        >
          Hủy
        </button>
        <button
          onClick={onSubmit}
          disabled={submitting || !hasItems}
          className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Xác nhận trả hàng'}
        </button>
      </div>
    </div>
  );
}
