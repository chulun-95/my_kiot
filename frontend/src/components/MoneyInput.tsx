import type { InputHTMLAttributes } from 'react';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'inputMode'
> & {
  value: number | string | null | undefined;
  onChange: (value: number) => void;
  /** Hiển thị giá trị 0 thành ô trống thay vì "0". Dùng cho ô tiền khách đưa POS. */
  showZeroAsEmpty?: boolean;
  /** Ẩn nhãn VNĐ phía bên phải input — dùng khi parent đã đặt ký hiệu ₫ riêng. */
  hideCurrency?: boolean;
};

const formatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

function toDisplay(
  v: number | string | null | undefined,
  showZeroAsEmpty: boolean,
): string {
  if (v === null || v === undefined || v === '') return '';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '';
  if (showZeroAsEmpty && n === 0) return '';
  return formatter.format(Math.max(0, Math.round(n)));
}

export default function MoneyInput({
  value,
  onChange,
  className = '',
  showZeroAsEmpty = false,
  hideCurrency = false,
  ...rest
}: Props) {
  const display = toDisplay(value, showZeroAsEmpty);
  return (
    <span className="relative inline-block w-full">
      <input
        type="text"
        inputMode="numeric"
        value={display}
        onChange={(e) => {
          const digits = e.target.value.replace(/[^\d]/g, '');
          onChange(digits === '' ? 0 : Number(digits));
        }}
        className={`${className} ${hideCurrency ? '' : 'pr-12'} text-right`}
        {...rest}
      />
      {!hideCurrency && (
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 select-none">
          VNĐ
        </span>
      )}
    </span>
  );
}
