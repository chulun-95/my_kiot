import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import * as customerApi from '../../api/customer';
import type { CustomerResponse } from '../../api/customer';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

interface Props {
  mode: 'create' | 'edit';
  initial?: CustomerResponse;
  onSaved?: (customer: CustomerResponse) => void;
  onCancel?: () => void;
}

export default function CustomerForm({ mode, initial, onSaved, onCancel }: Props) {
  const navigate = useNavigate();
  const [name, setName] = useState(initial?.name ?? '');
  const [phone, setPhone] = useState(initial?.phone ?? '');
  const [email, setEmail] = useState(initial?.email ?? '');
  const [address, setAddress] = useState(initial?.address ?? '');
  const [note, setNote] = useState(initial?.note ?? '');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = {
        name,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
        address: address || undefined,
        note: note || undefined,
      };
      if (mode === 'create') {
        const created = await customerApi.createCustomer(payload);
        if (onSaved) onSaved(created);
        else navigate(`/customers/${created.id}`);
      } else if (initial) {
        const updated = await customerApi.updateCustomer(initial.id, payload);
        if (onSaved) onSaved(updated);
      }
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-3 bg-white p-5 rounded border border-slate-200 max-w-xl"
    >
      <h2 className="text-lg font-semibold">
        {mode === 'create' ? 'Thêm khách hàng' : 'Sửa khách hàng'}
      </h2>
      <label className="block">
        <span className="text-sm text-slate-700">Tên *</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          minLength={1}
          maxLength={200}
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          {...viValidity({
            valueMissing: 'Vui lòng nhập tên khách hàng',
            tooLong: 'Tên tối đa 200 ký tự',
          })}
        />
      </label>
      <label className="block">
        <span className="text-sm text-slate-700">Số điện thoại</span>
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          maxLength={20}
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          {...viValidity({ tooLong: 'Số điện thoại tối đa 20 ký tự' })}
        />
        <span className="text-xs text-slate-500">
          Định dạng VN: bắt đầu 03/05/07/08/09, 10 chữ số
        </span>
      </label>
      <label className="block">
        <span className="text-sm text-slate-700">Email</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          {...viValidity({ typeMismatch: 'Email không hợp lệ' })}
        />
      </label>
      <label className="block">
        <span className="text-sm text-slate-700">Địa chỉ</span>
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
        />
      </label>
      <label className="block">
        <span className="text-sm text-slate-700">Ghi chú</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
        />
      </label>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel ?? (() => navigate(-1))}
          className="px-3 py-2 rounded border border-slate-300"
        >
          Hủy
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Lưu'}
        </button>
      </div>
    </form>
  );
}
