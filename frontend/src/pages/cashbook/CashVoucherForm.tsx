import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import * as cashApi from '../../api/cashbook';
import type { CashDirection, CashMethod } from '../../api/cashbook';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

const IN_CATEGORIES = [
  { value: 'OTHER_IN', label: 'Thu khác' },
  { value: 'CAPITAL', label: 'Góp vốn' },
];
const OUT_CATEGORIES = [
  { value: 'SALARY', label: 'Chi lương' },
  { value: 'OPERATING', label: 'Chi phí vận hành' },
  { value: 'OTHER_OUT', label: 'Chi khác' },
];

export default function CashVoucherForm() {
  const navigate = useNavigate();
  const [direction, setDirection] = useState<CashDirection>('IN');
  const [method, setMethod] = useState<CashMethod>('CASH');
  const [category, setCategory] = useState('OTHER_IN');
  const [amount, setAmount] = useState('');
  const [partnerName, setPartnerName] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const cats = direction === 'IN' ? IN_CATEGORIES : OUT_CATEGORIES;

  const onChangeDirection = (d: CashDirection) => {
    setDirection(d);
    setCategory(d === 'IN' ? 'OTHER_IN' : 'SALARY');
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const amt = Number(amount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setError('Số tiền phải lớn hơn 0');
      return;
    }
    setSubmitting(true);
    try {
      await cashApi.createCash({
        direction, method, category, amount: amt,
        partner_name: partnerName || undefined, note: note || undefined,
      });
      navigate('/cash-book');
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Lập phiếu thu/chi</h1>
      <form onSubmit={onSubmit} className="space-y-3 bg-white p-5 rounded border border-slate-200">
        <div className="flex gap-2">
          <button type="button" onClick={() => onChangeDirection('IN')}
            className={`px-3 py-2 rounded border ${direction === 'IN' ? 'bg-emerald-600 text-white border-emerald-600' : 'border-slate-300'}`}>
            Phiếu thu
          </button>
          <button type="button" onClick={() => onChangeDirection('OUT')}
            className={`px-3 py-2 rounded border ${direction === 'OUT' ? 'bg-rose-600 text-white border-rose-600' : 'border-slate-300'}`}>
            Phiếu chi
          </button>
        </div>

        <label className="block">
          <span className="text-sm text-slate-700">Loại</span>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            aria-label="Loại"
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded">
            {cats.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Phương thức</span>
          <select value={method} onChange={(e) => setMethod(e.target.value as CashMethod)}
            aria-label="Phương thức"
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded">
            <option value="CASH">Tiền mặt</option>
            <option value="BANK_TRANSFER">Chuyển khoản</option>
            <option value="EWALLET">Ví điện tử</option>
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Số tiền *</span>
          <input type="number" min="1" step="1" required value={amount}
            onChange={(e) => setAmount(e.target.value)}
            aria-label="Số tiền"
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded text-right"
            {...viValidity({ valueMissing: 'Vui lòng nhập số tiền', rangeUnderflow: 'Số tiền phải lớn hơn 0' })} />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Người nộp/nhận</span>
          <input value={partnerName} onChange={(e) => setPartnerName(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded" />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Ghi chú</span>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded" />
        </label>

        {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={() => navigate('/cash-book')}
            className="px-3 py-2 rounded border border-slate-300">Hủy</button>
          <button type="submit" disabled={submitting}
            className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50">
            {submitting ? 'Đang lưu...' : 'Lưu phiếu'}
          </button>
        </div>
      </form>
    </div>
  );
}
