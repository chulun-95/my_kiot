import dayjs from 'dayjs';

export interface DateRange {
  from: string;
  to: string;
}

export function defaultRangeLast30(): DateRange {
  const to = dayjs().format('YYYY-MM-DD');
  const from = dayjs().subtract(30, 'day').format('YYYY-MM-DD');
  return { from, to };
}

interface Props {
  value: DateRange;
  onChange: (next: DateRange) => void;
}

export default function DateRangePicker({ value, onChange }: Props) {
  const invalid = Boolean(value.from && value.to && value.from > value.to);
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-sm">
        <span className="block text-slate-600 mb-1">Từ ngày</span>
        <input
          type="date"
          aria-label="Từ ngày"
          value={value.from}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      <label className="text-sm">
        <span className="block text-slate-600 mb-1">Đến ngày</span>
        <input
          type="date"
          aria-label="Đến ngày"
          value={value.to}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      {invalid && (
        <span role="alert" className="text-sm text-rose-600">
          Khoảng ngày không hợp lệ
        </span>
      )}
    </div>
  );
}
