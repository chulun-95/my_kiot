import type { InputHTMLAttributes } from 'react';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'inputMode'
> & {
  value: number | string | null | undefined;
  onChange: (value: number) => void;
};

const formatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

function toDisplay(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '';
  return formatter.format(Math.max(0, Math.round(n)));
}

export default function MoneyInput({
  value,
  onChange,
  className = '',
  ...rest
}: Props) {
  const display = toDisplay(value);
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
        className={`${className} pr-12 text-right`}
        {...rest}
      />
      <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 select-none">
        VNĐ
      </span>
    </span>
  );
}
