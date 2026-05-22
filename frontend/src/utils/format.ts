import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

const TZ = 'Asia/Ho_Chi_Minh';
const vndFormatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

export function formatVND(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '0 đ';
  const n = typeof amount === 'string' ? Number(amount) : amount;
  if (!Number.isFinite(n)) return '0 đ';
  return `${vndFormatter.format(Math.round(n))} đ`;
}

export function formatDate(
  value: string | Date | null | undefined,
  fmt: string = 'DD/MM/YYYY HH:mm',
): string {
  if (!value) return '';
  const d = dayjs(value);
  if (!d.isValid()) return '';
  try {
    return d.tz(TZ).format(fmt);
  } catch {
    return d.format(fmt);
  }
}

export function formatQty(qty: number | string | null | undefined): string {
  if (qty === null || qty === undefined || qty === '') return '0';
  const n = typeof qty === 'string' ? Number(qty) : qty;
  if (!Number.isFinite(n)) return '0';
  const fixed = n.toFixed(3);
  return fixed.replace(/\.?0+$/, '');
}
