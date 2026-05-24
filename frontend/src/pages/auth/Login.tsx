import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import type { TenantOption } from '../../stores/authStore';
import { toFriendlyMessage, extractApiError } from '../../utils/errors';

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [tenants, setTenants] = useState<TenantOption[] | null>(null);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(phone, password, tenantId ?? undefined);
      if (result && result.requires_tenant_selection) {
        setTenants(result.tenants);
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      const api = extractApiError(err);
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 429 || api?.code === 'ACCOUNT_LOCKED') {
        setError('Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau');
      } else {
        setError(toFriendlyMessage(err, 'Sai số điện thoại hoặc mật khẩu'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm p-6 bg-white rounded shadow border border-slate-200 space-y-4"
      >
        <h1 className="text-xl font-semibold">Đăng nhập</h1>

        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            autoFocus
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="login-password" className="text-sm text-slate-700">
              Mật khẩu
            </label>
            <button
              type="button"
              onClick={() => setForgotOpen(true)}
              className="text-xs text-slate-600 underline hover:text-slate-900"
            >
              Quên mật khẩu?
            </button>
          </div>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </div>

        {tenants && tenants.length > 0 && (
          <fieldset className="space-y-2">
            <legend className="text-sm text-slate-700">Chọn shop</legend>
            {tenants.map((t) => (
              <label key={t.id} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="tenant"
                  value={t.id}
                  checked={tenantId === t.id}
                  onChange={() => setTenantId(t.id)}
                />
                {t.name} <span className="text-slate-500">({t.role})</span>
              </label>
            ))}
          </fieldset>
        )}

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
          {submitting ? 'Đang xử lý...' : 'Đăng nhập'}
        </button>

        <div className="text-sm text-slate-600">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-slate-900 underline">
            Đăng ký shop mới
          </Link>
        </div>
      </form>

      {forgotOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Lấy lại mật khẩu"
          className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50 p-4"
          onClick={() => setForgotOpen(false)}
        >
          <div
            className="w-full max-w-sm bg-white rounded shadow-lg p-5 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold">Lấy lại mật khẩu</h2>
            <p className="text-sm text-slate-700">
              Vui lòng liên hệ admin để được hỗ trợ đặt lại mật khẩu.
            </p>
            <a
              href="https://zalo.me/0392368532"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-3 rounded bg-sky-600 text-white font-medium hover:bg-sky-700"
            >
              Liên hệ qua Zalo
            </a>
            <a
              href="https://www.facebook.com/profile.php?id=61579076336752&sk=directory_personal_details"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-3 rounded bg-blue-700 text-white font-medium hover:bg-blue-800"
            >
              Liên hệ qua Facebook
            </a>
            <button
              type="button"
              onClick={() => setForgotOpen(false)}
              className="w-full py-2 rounded border border-slate-300 text-sm"
            >
              Đóng
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
