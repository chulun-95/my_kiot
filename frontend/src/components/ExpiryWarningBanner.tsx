import { useState } from 'react';
import { useSubscriptionStatus } from '../hooks/useSubscriptionStatus';

const FACEBOOK_URL = 'https://www.facebook.com/profile.php?id=61579076336752';
const ZALO_URL = 'https://zalo.me/0392368532';
const DISMISS_KEY = 'expiry_banner_dismissed';

export default function ExpiryWarningBanner() {
  const { isExpired, daysUntilExpiry } = useSubscriptionStatus();
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(DISMISS_KEY) === '1',
  );

  const shouldShow =
    !isExpired && daysUntilExpiry !== null && daysUntilExpiry <= 7 && !dismissed;

  if (!shouldShow) return null;

  const onDismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, '1');
    setDismissed(true);
  };

  return (
    <div className="w-full bg-amber-50 border-b border-amber-200 text-amber-900 px-4 py-2 text-sm flex items-center justify-between gap-3">
      <span>
        ⚠️ Gói dịch vụ sắp hết hạn sau {daysUntilExpiry} ngày nữa. Liên hệ để gia
        hạn.{' '}
        <a
          href={FACEBOOK_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="underline font-medium"
        >
          Facebook
        </a>{' '}
        ·{' '}
        <a
          href={ZALO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="underline font-medium"
        >
          Zalo
        </a>
      </span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Đóng thông báo"
        className="text-amber-700 hover:text-amber-900 shrink-0"
      >
        ✕
      </button>
    </div>
  );
}
