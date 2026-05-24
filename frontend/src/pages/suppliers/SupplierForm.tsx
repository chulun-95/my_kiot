import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as supplierApi from '../../api/supplier';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

export default function SupplierForm() {
  const params = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const supplierId = params.id ? Number(params.id) : null;
  const mode: 'create' | 'edit' = supplierId != null ? 'edit' : 'create';

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [taxCode, setTaxCode] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== 'edit' || supplierId == null) return;
    setLoading(true);
    (async () => {
      try {
        const s = await supplierApi.getSupplier(supplierId);
        setName(s.name);
        setPhone(s.phone ?? '');
        setEmail(s.email ?? '');
        setAddress(s.address ?? '');
        setTaxCode(s.tax_code ?? '');
        setNote(s.note ?? '');
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [mode, supplierId]);

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
        tax_code: taxCode.trim() || undefined,
        note: note || undefined,
      };
      if (mode === 'create') {
        await supplierApi.createSupplier(payload);
      } else if (supplierId != null) {
        await supplierApi.updateSupplier(supplierId, payload);
      }
      navigate('/suppliers');
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-4 text-slate-500">Đang tải...</div>;

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">
        {mode === 'create' ? 'Thêm nhà cung cấp' : 'Sửa nhà cung cấp'}
      </h1>
      <form
        onSubmit={onSubmit}
        className="space-y-3 bg-white p-5 rounded border border-slate-200"
      >
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
              valueMissing: 'Vui lòng nhập tên nhà cung cấp',
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
          <span className="text-sm text-slate-700">Mã số thuế</span>
          <input
            value={taxCode}
            onChange={(e) => setTaxCode(e.target.value)}
            maxLength={20}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({ tooLong: 'Mã số thuế tối đa 20 ký tự' })}
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
            onClick={() => navigate(-1)}
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
