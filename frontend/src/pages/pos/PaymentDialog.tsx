import { useState, useEffect, useRef, type KeyboardEvent } from 'react';
import type { PaymentMethod, PaymentInput } from '../../api/invoice';
import { toFriendlyMessage } from '../../utils/errors';
import MoneyInput from '../../components/MoneyInput';

interface Props {
  open: boolean;
  total: number;
  hasCustomer: boolean;
  onClose: () => void;
  onComplete: (
    payments: PaymentInput[],
    allowDebt: boolean,
    payInFull: boolean,
  ) => Promise<void>;
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

const numFormatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });
const formatNumber = (n: number) => numFormatter.format(Math.round(Math.max(0, n)));

export default function PaymentDialog({
  open,
  total,
  hasCustomer,
  onClose,
  onComplete,
}: Props) {
  const [rows, setRows] = useState<PaymentRow[]>([
    { method: 'CASH', amount: 0 },
  ]);
  const [allowDebt, setAllowDebt] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const completeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      setRows([{ method: 'CASH', amount: 0 }]);
      setAllowDebt(false);
      setError(null);
    }
  }, [open, total]);

  if (!open) return null;

  const paid = rows.reduce((s, r) => s + (r.amount || 0), 0);
  const noAmountEntered = paid === 0;
  // payInFull: không nhập tiền + không chọn nợ → coi như trả đúng đủ
  const payInFull = noAmountEntered && !allowDebt;
  const effectivePaid = payInFull ? total : paid;
  const change = Math.max(0, effectivePaid - total);
  const missing = Math.max(0, total - effectivePaid);
  const treatAsExact = payInFull;

  const updateRow = (idx: number, patch: Partial<PaymentRow>) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };
  const addRow = () =>
    setRows((prev) => [...prev, { method: 'CASH', amount: 0 }]);
  const removeRow = (idx: number) =>
    setRows((prev) => prev.filter((_, i) => i !== idx));

  const handleComplete = async () => {
    if (submitting) return;
    if (missing > 0 && !hasCustomer) {
      setError('Bán nợ phải chọn khách hàng — không thể ghi nợ cho khách vãng lai.');
      return;
    }
    if (missing > 0 && !allowDebt) {
      setError('Số tiền khách đưa chưa đủ. Bật "Cho phép nợ" để tiếp tục.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      let payments: PaymentInput[];
      if (treatAsExact) {
        // Gửi FE total để tránh trường hợp backend allow_debt=true nhận amount=0 mà accept.
        // Store sẽ override bằng backendTotal (authoritative) khi payInFull=true.
        const method = rows[0]?.method ?? 'CASH';
        payments = [{ method, amount: total }];
      } else {
        payments = rows
          .filter((r) => r.amount > 0)
          .map<PaymentInput>((r) => ({ method: r.method, amount: r.amount }));
      }
      await onComplete(payments, allowDebt, treatAsExact);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && (e.target as HTMLElement).tagName !== 'BUTTON') {
      e.preventDefault();
      void handleComplete();
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Thanh toán"
      onKeyDown={handleKeyDown}
      className="fixed inset-0 bg-slate-950/55 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]"
    >
      <div
        className="bg-white rounded-2xl shadow-[0_20px_60px_-15px_rgba(15,23,42,0.35)] ring-1 ring-slate-200/60 w-full max-w-md overflow-hidden"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <span className="text-[11px] font-semibold tracking-[0.22em] text-slate-500 uppercase">
            Thanh toán
          </span>
          <button
            onClick={onClose}
            className="text-[10px] tracking-wider text-slate-400 hover:text-slate-700 transition-colors flex items-center gap-1.5"
            aria-label="Đóng (Esc)"
          >
            <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-500">
              ESC
            </kbd>
          </button>
        </div>

        {/* Total — hero */}
        <div className="px-6 pb-5">
          <div className="text-[10px] font-semibold tracking-[0.28em] text-slate-400 uppercase mb-2.5">
            Tổng phải trả
          </div>
          <div className="flex items-baseline gap-2 whitespace-nowrap">
            <span
              aria-hidden
              className="text-3xl font-light text-slate-300 font-mono leading-none translate-y-[2px]"
            >
              ₫
            </span>
            <span className="text-[3.25rem] font-bold text-slate-900 tabular-nums leading-none tracking-[-0.02em] font-mono">
              {formatNumber(total)}
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-slate-100" />

        {/* Payment rows — ledger entries */}
        <div className="px-6 py-4 space-y-3">
          {rows.map((r, idx) => {
            const isCash = r.method === 'CASH';
            const rowNumber = (idx + 1).toString().padStart(2, '0');
            return (
              <div key={idx} className="flex items-start gap-3 group">
                {/* Row number */}
                <div className="pt-2 select-none">
                  <span className="text-[10px] font-mono text-slate-300 tracking-wider tabular-nums">
                    {rowNumber}
                  </span>
                </div>

                {/* Method picker (full-width) + amount input stacked */}
                <div className="flex-1 space-y-1.5 min-w-0">
                  {/* Method picker — full width, standalone */}
                  <label
                    className="relative flex items-center gap-2 px-3 py-2 rounded-md bg-slate-50 ring-1 ring-slate-200 hover:ring-slate-300 hover:bg-slate-100/80 focus-within:ring-slate-900 focus-within:bg-white transition-all cursor-pointer group/method"
                  >
                    <span
                      aria-hidden
                      className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"
                    />
                    <select
                      value={r.method}
                      onChange={(e) =>
                        updateRow(idx, {
                          method: e.target.value as PaymentMethod,
                        })
                      }
                      aria-label={`Phương thức thanh toán ${idx + 1}`}
                      className="appearance-none bg-transparent flex-1 text-[11px] font-semibold tracking-[0.14em] uppercase text-slate-700 cursor-pointer focus:outline-none pr-5"
                    >
                      {METHODS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                    <svg
                      aria-hidden
                      width="10"
                      height="6"
                      viewBox="0 0 10 6"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none group-hover/method:text-slate-700 transition-colors"
                    >
                      <path
                        d="M1 1l4 4 4-4"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </label>

                  {/* Amount input — full width */}
                  <div className="flex items-baseline gap-2 px-3 py-2.5 rounded-md ring-1 ring-slate-200 bg-white hover:ring-slate-300 focus-within:ring-slate-900 focus-within:shadow-[0_0_0_3px_rgba(15,23,42,0.05)] transition-all">
                    <span
                      aria-hidden
                      className="text-base font-light text-slate-300 font-mono leading-none translate-y-[2px] select-none"
                    >
                      ₫
                    </span>
                    <MoneyInput
                      value={r.amount}
                      onChange={(v) => updateRow(idx, { amount: v })}
                      aria-label={
                        isCash
                          ? `Tiền khách đưa ${idx + 1}`
                          : `Số tiền ${idx + 1}`
                      }
                      placeholder={isCash ? 'Tiền khách đưa…' : 'Số tiền'}
                      hideCurrency
                      autoFocus={idx === 0}
                      className="flex-1 min-w-0 bg-transparent text-right text-xl font-semibold text-slate-900 placeholder:text-slate-300 placeholder:font-normal placeholder:text-[13px] focus:outline-none tabular-nums font-mono"
                    />
                  </div>
                </div>

                {/* Remove row */}
                {rows.length > 1 ? (
                  <button
                    onClick={() => removeRow(idx)}
                    className="text-slate-300 hover:text-rose-600 transition-colors text-base w-6 h-9 flex items-center justify-center mt-px"
                    aria-label={`Xóa dòng thanh toán ${idx + 1}`}
                  >
                    ✕
                  </button>
                ) : (
                  <span aria-hidden className="w-6 shrink-0" />
                )}
              </div>
            );
          })}

          <div className="pl-7">
            <button
              onClick={addRow}
              className="inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.14em] uppercase text-slate-400 hover:text-slate-900 transition-colors"
              type="button"
            >
              <span className="text-base leading-none translate-y-[-1px]">＋</span>
              <span>Thêm phương thức</span>
            </button>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-slate-100" />

        {/* Result strip */}
        {treatAsExact ? (
          <div className="px-6 py-4 space-y-2.5">
            <div className="text-xs text-slate-500 flex items-baseline justify-between">
              <span>Để trống nếu khách trả đúng đủ</span>
              <span className="text-slate-400">
                bấm{' '}
                <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-600">
                  Enter
                </kbd>{' '}
                là xong
              </span>
            </div>
            {hasCustomer && (
              <label className="flex items-center gap-2 text-[11px] text-slate-600 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={allowDebt}
                  onChange={(e) => setAllowDebt(e.target.checked)}
                  aria-label="Cho phép nợ"
                  className="accent-rose-600"
                />
                Ghi nợ — khách chưa trả lần này
              </label>
            )}
          </div>
        ) : change > 0 ? (
          <div
            role="status"
            aria-label="Tiền thừa cho khách"
            className="px-6 py-4 bg-emerald-50/80 border-t border-emerald-100 flex items-baseline justify-between"
          >
            <span className="text-[10px] font-semibold tracking-[0.25em] text-emerald-700 uppercase">
              Tiền thừa
            </span>
            <div className="flex items-baseline gap-1.5 whitespace-nowrap">
              <span
                aria-hidden
                className="text-xl font-light text-emerald-400 font-mono leading-none translate-y-[1px]"
              >
                ₫
              </span>
              <span className="text-3xl font-bold text-emerald-700 tabular-nums leading-none tracking-tight font-mono">
                {formatNumber(change)}
              </span>
            </div>
          </div>
        ) : missing > 0 ? (
          <div className="px-6 py-4 bg-rose-50/80 border-t border-rose-100 space-y-2.5">
            <div className="flex items-baseline justify-between">
              <span className="text-[10px] font-semibold tracking-[0.25em] text-rose-700 uppercase">
                Còn thiếu
              </span>
              <div className="flex items-baseline gap-1.5 whitespace-nowrap">
                <span
                  aria-hidden
                  className="text-xl font-light text-rose-400 font-mono leading-none translate-y-[1px]"
                >
                  ₫
                </span>
                <span className="text-3xl font-bold text-rose-700 tabular-nums leading-none tracking-tight font-mono">
                  {formatNumber(missing)}
                </span>
              </div>
            </div>
            {hasCustomer ? (
              <label className="flex items-center gap-2 text-[11px] text-rose-700 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={allowDebt}
                  onChange={(e) => setAllowDebt(e.target.checked)}
                  aria-label="Cho phép nợ"
                  className="accent-rose-600"
                />
                Cho phép nợ — khách trả thiếu
              </label>
            ) : (
              <p className="text-[11px] text-rose-700 leading-relaxed">
                Phải chọn khách hàng mới được bán nợ — khoản nợ của khách vãng lai
                sẽ không được thống kê. Hãy chọn khách hàng ở ô phía trên.
              </p>
            )}
          </div>
        ) : (
          <div className="px-6 py-4 text-xs text-slate-500">
            Khách đưa vừa đủ — không cần thối lại.
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="px-6 pb-3 text-xs text-rose-600"
          >
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="px-6 py-4 bg-slate-50/60 border-t border-slate-100 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-4 py-2.5 text-sm text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
          >
            Đóng
          </button>
          <button
            ref={completeBtnRef}
            onClick={handleComplete}
            disabled={submitting}
            className="group px-5 py-2.5 rounded-lg bg-emerald-700 text-white text-sm font-semibold shadow-sm shadow-emerald-700/20 hover:bg-emerald-800 active:bg-emerald-900 transition-colors disabled:opacity-60 flex items-center gap-2.5"
          >
            <span>{submitting ? 'Đang xử lý…' : 'Hoàn tất'}</span>
            {!submitting && (
              <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/15 text-white/80 group-hover:bg-white/20 transition-colors">
                ↵
              </kbd>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
