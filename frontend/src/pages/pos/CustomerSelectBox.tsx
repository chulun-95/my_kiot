import CustomerQuickSearch from '../../components/CustomerQuickSearch';
import type { CustomerResponse } from '../../api/customer';

interface Props {
  customerId: number | null;
  customerName: string | null;
  onChange: (id: number | null, name: string | null) => void;
  resetKey?: number;
}

export default function CustomerSelectBox({
  customerId,
  customerName,
  onChange,
  resetKey = 0,
}: Props) {
  const handle = (c: CustomerResponse | null) => {
    if (c) onChange(c.id, c.name);
    else onChange(null, null);
  };

  const displayName = customerId ? customerName ?? 'Đã chọn' : 'Vãng lai';

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">Khách:</span>
        <span
          className={`font-semibold ${
            customerId ? 'text-slate-900' : 'text-slate-500 italic'
          }`}
        >
          {displayName}
        </span>
      </div>
      <CustomerQuickSearch key={resetKey} onPick={handle} allowGuest />
    </div>
  );
}
