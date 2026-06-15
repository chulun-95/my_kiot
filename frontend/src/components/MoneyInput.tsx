import { useLayoutEffect, useRef } from 'react';
import type {
  ChangeEvent,
  ClipboardEvent,
  FocusEvent,
  InputHTMLAttributes,
  KeyboardEvent,
} from 'react';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'inputMode'
> & {
  value: number | string | null | undefined;
  onChange: (value: number) => void;
  /** Ẩn nhãn "VNĐ" phía bên phải input — dùng khi parent đã đặt ký hiệu ₫ riêng. */
  hideCurrency?: boolean;
};

const formatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

const DIGIT_KEYS = new Set([
  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
]);

const PASSTHROUGH_KEYS = new Set([
  'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
  'Home', 'End', 'Tab', 'Enter', 'Escape', 'Shift',
]);

function normalizeValue(v: number | string | null | undefined): number {
  if (v === null || v === undefined || v === '') return 0;
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.round(n);
}

function toDisplay(v: number): string {
  if (v === 0) return '';
  return formatter.format(v);
}

function floorToHundred(n: number): number {
  return Math.floor(n / 100) * 100;
}

export default function MoneyInput({
  value,
  onChange,
  className = '',
  hideCurrency = false,
  disabled,
  onFocus,
  onKeyDown: outerKeyDown,
  ...rest
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const numericValue = normalizeValue(value);
  const display = toDisplay(numericValue);

  useLayoutEffect(() => {
    const el = inputRef.current;
    if (el && document.activeElement === el) {
      const end = el.value.length;
      el.setSelectionRange(end, end);
    }
  }, [display]);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    if (DIGIT_KEYS.has(e.key)) {
      e.preventDefault();
      const digit = Number(e.key);
      onChange(numericValue * 10 + digit * 100);
      return;
    }

    if (e.key === 'Backspace' || e.key === 'Delete') {
      e.preventDefault();
      if (numericValue > 0) {
        if (numericValue % 100 !== 0) {
          // legacy non-multiple: first normalize to nearest 100
          onChange(floorToHundred(numericValue));
        } else {
          onChange(Math.floor(numericValue / 1000) * 100);
        }
      }
      return;
    }

    if (PASSTHROUGH_KEYS.has(e.key)) {
      outerKeyDown?.(e);
      return;
    }

    e.preventDefault();
  }

  function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    if (disabled) return;
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    const digits = text.replace(/\D/g, '');
    if (digits === '') return;
    onChange(floorToHundred(Number(digits)));
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    if (disabled) return;
    const digits = e.target.value.replace(/\D/g, '');
    if (digits === '') {
      onChange(0);
      return;
    }
    onChange(floorToHundred(Number(digits)));
  }

  function handleFocus(e: FocusEvent<HTMLInputElement>) {
    const end = e.currentTarget.value.length;
    e.currentTarget.setSelectionRange(end, end);
    onFocus?.(e);
  }

  return (
    <span className="relative inline-block w-full">
      <input
        {...rest}
        ref={inputRef}
        type="text"
        inputMode="numeric"
        value={display}
        disabled={disabled}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onFocus={handleFocus}
        className={`${className} ${hideCurrency ? '' : 'pr-12'} text-right`}
      />
      {!hideCurrency && (
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 select-none">
          VNĐ
        </span>
      )}
    </span>
  );
}
