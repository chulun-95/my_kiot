import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';
import PasswordInput from '../../components/PasswordInput';

export default function Register() {
  const navigate = useNavigate();
  const register = useAuthStore((s) => s.register);
  const [shopName, setShopName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!/^0\d{9}$/.test(phone)) {
      setError('Số điện thoại phải có 10 chữ số, bắt đầu bằng 0');
      return;
    }
    if (password !== confirmPassword) {
      setError('Xác nhận mật khẩu không khớp');
      return;
    }
    setSubmitting(true);
    try {
      await register({
        shop_name: shopName,
        phone,
        address,
        password,
        confirm_password: confirmPassword,
      });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md p-6 bg-white rounded shadow border border-slate-200 space-y-4"
      >
        <h1 className="text-xl font-semibold">Đăng ký shop mới</h1>

        <label className="block">
          <span className="text-sm text-slate-700">Tên shop</span>
          <input
            value={shopName}
            onChange={(e) => setShopName(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng nhập tên shop',
              tooShort: 'Tên shop phải có ít nhất 2 ký tự',
            })}
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng nhập số điện thoại',
            })}
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Địa chỉ</span>
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            rows={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng nhập địa chỉ',
            })}
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu</span>
          <PasswordInput
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            wrapperClass="mt-1"
            {...viValidity({
              valueMissing: 'Vui lòng nhập mật khẩu',
              tooShort: 'Mật khẩu phải có ít nhất 6 ký tự',
            })}
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Nhập lại mật khẩu</span>
          <PasswordInput
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
            wrapperClass="mt-1"
            {...viValidity({
              valueMissing: 'Vui lòng nhập lại mật khẩu',
              tooShort: 'Mật khẩu phải có ít nhất 6 ký tự',
            })}
          />
        </label>

        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang xử lý...' : 'Đăng ký'}
        </button>

        <div className="text-sm text-slate-600">
          Đã có tài khoản?{' '}
          <Link to="/login" className="text-slate-900 underline">
            Đăng nhập
          </Link>
        </div>
      </form>
    </div>
  );
}
