import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react';
import type { AxiosError } from 'axios';
import * as customerApi from '../api/customer';
import type { CustomerResponse } from '../api/customer';
import { toFriendlyMessage } from '../utils/errors';

interface Props {
  onPick: (customer: CustomerResponse | null) => void;
  allowGuest?: boolean;
  initial?: string;
}

export default function CustomerQuickSearch({
  onPick,
  allowGuest = true,
  initial = '',
}: Props) {
  const [phone, setPhone] = useState(initial);
  const [picked, setPicked] = useState<CustomerResponse | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setNotFound(false);
    setPicked(null);
  }, [phone]);

  const lookup = async () => {
    const p = phone.trim();
    if (!/^\d{9,11}$/.test(p)) {
      setError('Số điện thoại không hợp lệ');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const c = await customerApi.getCustomerByPhone(p);
      setPicked(c);
      onPick(c);
      setNotFound(false);
    } catch (err) {
      const ax = err as AxiosError;
      if (ax.response?.status === 404) {
        setNotFound(true);
      } else {
        setError(toFriendlyMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      lookup();
    }
  };

  const createNew = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const created = await customerApi.createCustomer({
        name: newName,
        phone: phone.trim(),
      });
      setPicked(created);
      onPick(created);
      setNotFound(false);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => {
            if (phone.trim() && !picked) lookup();
          }}
          placeholder="SĐT khách hàng"
          aria-label="Số điện thoại khách hàng"
          className="px-3 py-2 border border-slate-300 rounded flex-1"
        />
        <button
          type="button"
          onClick={lookup}
          disabled={loading}
          className="px-3 py-2 rounded border border-slate-300 disabled:opacity-50"
        >
          Tìm
        </button>
        {allowGuest && (
          <button
            type="button"
            onClick={() => {
              setPicked(null);
              setNotFound(false);
              onPick(null);
            }}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Khách vãng lai
          </button>
        )}
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      {picked && (
        <div className="text-sm text-emerald-700">
          Đã chọn: {picked.name} ({picked.phone ?? '-'})
        </div>
      )}

      {notFound && (
        <form
          onSubmit={createNew}
          className="bg-white border border-slate-200 rounded p-3 space-y-2"
        >
          <div className="text-sm text-slate-600">
            Không tìm thấy. Thêm khách mới?
          </div>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Tên khách hàng"
            required
            className="w-full px-3 py-2 border border-slate-300 rounded"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
          >
            {loading ? 'Đang lưu...' : 'Thêm khách mới'}
          </button>
        </form>
      )}
    </div>
  );
}
