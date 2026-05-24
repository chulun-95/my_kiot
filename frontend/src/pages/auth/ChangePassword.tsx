import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { changePassword } from '../../api/auth';
import { toFriendlyMessage } from '../../utils/errors';
import { viValidity } from '../../utils/validity';

export default function ChangePassword() {
  const navigate = useNavigate();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return;
    }
    if (newPassword.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự');
      return;
    }
    setSubmitting(true);
    try {
      const pair = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setAccessToken(pair.access_token);
      setSuccess('Đổi mật khẩu thành công');
      setTimeout(() => navigate('/dashboard'), 800);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-semibold mb-4">Đổi mật khẩu</h1>
      <form
        onSubmit={onSubmit}
        className="space-y-4 bg-white p-4 rounded border border-slate-200"
      >
        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu hiện tại</span>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({ valueMissing: 'Vui lòng nhập mật khẩu hiện tại' })}
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu mới</span>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng nhập mật khẩu mới',
              tooShort: 'Mật khẩu mới phải có ít nhất 6 ký tự',
            })}
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Xác nhận mật khẩu</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            {...viValidity({
              valueMissing: 'Vui lòng xác nhận mật khẩu',
              tooShort: 'Mật khẩu phải có ít nhất 6 ký tự',
            })}
          />
        </label>
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        {success && (
          <div role="status" className="text-sm text-emerald-600">
            {success}
          </div>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Lưu'}
        </button>
      </form>
    </div>
  );
}
