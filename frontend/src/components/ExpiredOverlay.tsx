import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useSubscriptionStatus } from '../hooks/useSubscriptionStatus';

const FACEBOOK_URL = 'https://www.facebook.com/profile.php?id=61579076336752';
const ZALO_URL = 'https://zalo.me/0392368532';

export default function ExpiredOverlay() {
  const navigate = useNavigate();
  const doLogout = useAuthStore((s) => s.doLogout);
  const { isExpired } = useSubscriptionStatus();

  if (!isExpired) return null;

  const onLogout = async () => {
    await doLogout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/90 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-xl p-6 text-center space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Gói dịch vụ đã hết hạn
        </h2>
        <p className="text-sm text-slate-600">
          Vui lòng liên hệ để gia hạn và tiếp tục sử dụng dịch vụ.
        </p>
        <div className="space-y-2 pt-2">
          <button
            type="button"
            onClick={() => window.open(FACEBOOK_URL, '_blank')}
            className="w-full py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Liên hệ Facebook
          </button>
          <button
            type="button"
            onClick={() => window.open(ZALO_URL, '_blank')}
            className="w-full py-2 rounded bg-sky-500 text-white hover:bg-sky-600"
          >
            Liên hệ Zalo
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="w-full py-2 rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            Đăng xuất
          </button>
        </div>
      </div>
    </div>
  );
}
