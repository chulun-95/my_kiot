import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import type { AxiosError } from 'axios';
import * as customerApi from '../api/customer';
import type { CustomerResponse } from '../api/customer';
import { toFriendlyMessage } from '../utils/errors';
import { viValidity } from '../utils/validity';

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
  const lookupSeq = useRef(0);

  useEffect(() => {
    setNotFound(false);
    setPicked(null);
  }, [phone]);

  const lookup = async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent ?? false;
    const p = phone.trim();
    if (!/^\d{9,11}$/.test(p)) {
      if (!silent) setError('Số điện thoại không hợp lệ');
      return;
    }
    setError(null);
    setLoading(true);
    const seq = ++lookupSeq.current;
    try {
      const c = await customerApi.getCustomerByPhone(p);
      if (seq !== lookupSeq.current) return;  // outdated response
      setPicked(c);
      onPick(c);
      setNotFound(false);
    } catch (err) {
      if (seq !== lookupSeq.current) return;
      const ax = err as AxiosError;
      if (ax.response?.status === 404) {
        if (!silent) setNotFound(true);
      } else if (!silent) {
        setError(toFriendlyMessage(err));
      }
    } finally {
      if (seq === lookupSeq.current) setLoading(false);
    }
  };

  // Auto-lookup khi vừa đủ 10 số (định dạng VN phổ biến): debounce nhẹ để gõ xong mới tra
  useEffect(() => {
    const p = phone.trim();
    if (!/^\d{10}$/.test(p)) return;
    if (picked && picked.phone === p) return;
    const handle = setTimeout(() => {
      void lookup({ silent: true });
    }, 250);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phone]);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void lookup();
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
            if (phone.trim() && !picked) void lookup();
          }}
          placeholder="SĐT khách hàng"
          aria-label="Số điện thoại khách hàng"
          className="px-3 py-2 border border-slate-300 rounded flex-1"
        />
        <button
          type="button"
          onClick={() => void lookup()}
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
            {...viValidity({ valueMissing: 'Vui lòng nhập tên khách hàng' })}
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
