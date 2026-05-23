import { useState, useEffect } from 'react';
import type { PaymentMethod, PaymentInput } from '../../api/invoice';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

interface Props {
  open: boolean;
  total: number;
  onClose: () => void;
  onComplete: (payments: PaymentInput[], allowDebt: boolean) => Promise<void>;
}

interface PaymentRow {
  method: PaymentMethod;
  amount: number;
}

const METHODS: Array<{ value: PaymentMethod; label: string }> = [
  { value: 'CASH', label: 'Tiền mặt' },
  { value: 'BANK_TRANSFER', label: 'Chuyển khoản' },
  { value: 'MOMO', label: 'MoMo' },
  { value: 'VNPAY', label: 'VNPay' },
  { value: 'OTHER', label: 'Khác' },
];

export default function PaymentDialog({
  open,
  total,
  onClose,
  onComplete,
}: Props) {
  const [rows, setRows] = useState<PaymentRow[]>([
    { method: 'CASH', amount: total },
  ]);
  const [allowDebt, setAllowDebt] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setRows([{ method: 'CASH', amount: total }]);
      setAllowDebt(false);
      setError(null);
    }
  }, [open, total]);

  if (!open) return null;

  const paid = rows.reduce((s, r) => s + (r.amount || 0), 0);
  const change = Math.max(0, paid - total);
  const missing = Math.max(0, total - paid);

  const updateRow = (idx: number, patch: Partial<PaymentRow>) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };
  const addRow = () =>
    setRows((prev) => [...prev, { method: 'CASH', amount: 0 }]);
  const removeRow = (idx: number) =>
    setRows((prev) => prev.filter((_, i) => i !== idx));

  const handleComplete = async () => {
    if (submitting) return;
    if (missing > 0 && !allowDebt) {
      setError('Số tiền thanh toán chưa đủ. Bật "Cho phép nợ" để tiếp tục.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const payments = rows
        .filter((r) => r.amount > 0)
        .map<PaymentInput>((r) => ({ method: r.method, amount: r.amount }));
      await onComplete(payments, allowDebt);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Thanh toán"
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
    >
      <div className="bg-white rounded shadow-lg w-full max-w-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold">Thanh toán</h2>
        <div className="text-sm text-slate-600">
          Tổng phải trả: <span className="font-semibold text-slate-900">{formatVND(total)}</span>
        </div>

        <div className="space-y-2">
          {rows.map((r, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <select
                value={r.method}
                onChange={(e) =>
                  updateRow(idx, { method: e.target.value as PaymentMethod })
                }
                aria-label={`Phương thức thanh toán ${idx + 1}`}
                className="px-2 py-2 border border-slate-300 rounded"
              >
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="0"
                value={r.amount}
                onChange={(e) =>
                  updateRow(idx, { amount: Number(e.target.value) })
                }
                aria-label={`Số tiền ${idx + 1}`}
                className="flex-1 px-2 py-2 border border-slate-300 rounded text-right"
              />
              {rows.length > 1 && (
                <button
                  onClick={() => removeRow(idx)}
                  className="px-2 py-1 rounded border border-rose-300 text-rose-700 text-xs"
                  aria-label={`Xóa dòng thanh toán ${idx + 1}`}
                >
                  X
                </button>
              )}
            </div>
          ))}
          <button
            onClick={addRow}
            className="text-sm text-slate-700 underline"
            type="button"
          >
            + Thêm phương thức
          </button>
        </div>

        <div className="text-sm space-y-1 border-t border-slate-100 pt-3">
          <div className="flex justify-between">
            <span>Khách trả</span>
            <span>{formatVND(paid)}</span>
          </div>
          {change > 0 && (
            <div className="flex justify-between text-emerald-700">
              <span>Tiền thừa</span>
              <span>{formatVND(change)}</span>
            </div>
          )}
          {missing > 0 && (
            <div className="space-y-1">
              <div className="flex justify-between text-rose-700">
                <span>Còn thiếu</span>
                <span>{formatVND(missing)}</span>
              </div>
              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={allowDebt}
                  onChange={(e) => setAllowDebt(e.target.checked)}
                  aria-label="Cho phép nợ"
                />
                Cho phép nợ
              </label>
            </div>
          )}
        </div>

        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Đóng
          </button>
          <button
            onClick={handleComplete}
            disabled={submitting}
            className="px-4 py-2 rounded bg-emerald-700 text-white disabled:opacity-50"
          >
            {submitting ? 'Đang xử lý...' : 'Hoàn tất'}
          </button>
        </div>
      </div>
    </div>
  );
}
