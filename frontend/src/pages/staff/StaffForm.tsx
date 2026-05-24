import { useState, type FormEvent } from 'react';
import * as staffApi from '../../api/staff';
import type { StaffResponse } from '../../api/staff';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

interface Props {
  mode: 'create' | 'edit';
  initial?: StaffResponse;
  onClose: () => void;
  onSaved: () => void;
}

export default function StaffForm({ mode, initial, onClose, onSaved }: Props) {
  const [fullName, setFullName] = useState(initial?.full_name ?? '');
  const [phone, setPhone] = useState(initial?.phone ?? '');
  const [email, setEmail] = useState(initial?.email ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'create') {
        await staffApi.createStaff({
          full_name: fullName,
          phone,
          email: email || undefined,
          password,
        });
      } else if (initial) {
        await staffApi.updateStaff(initial.id, {
          full_name: fullName,
          email: email || undefined,
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50"
    >
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white p-5 rounded shadow space-y-3"
      >
        <h2 className="text-lg font-semibold">
          {mode === 'create' ? 'Thêm nhân viên' : 'Sửa nhân viên'}
        </h2>
        <label className="block">
          <span className="text-sm text-slate-700">Họ tên</span>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng nhập họ tên',
              tooShort: 'Họ tên phải có ít nhất 2 ký tự',
            })}
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone ?? ''}
            onChange={(e) => setPhone(e.target.value)}
            required={mode === 'create'}
            disabled={mode === 'edit'}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded disabled:bg-slate-100"
            {...viValidity({ valueMissing: 'Vui lòng nhập số điện thoại' })}
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Email (tùy chọn)</span>
          <input
            type="email"
            value={email ?? ''}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({ typeMismatch: 'Email không hợp lệ' })}
          />
        </label>
        {mode === 'create' && (
          <label className="block">
            <span className="text-sm text-slate-700">Mật khẩu khởi tạo</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
              {...viValidity({
                valueMissing: 'Vui lòng nhập mật khẩu',
                tooShort: 'Mật khẩu phải có ít nhất 6 ký tự',
              })}
            />
          </label>
        )}
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
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
    </div>
  );
}
