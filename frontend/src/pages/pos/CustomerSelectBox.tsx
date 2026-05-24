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

  return (
    <div className="space-y-2">
      {customerId && (
        <div className="text-sm text-slate-700">
          Khách: {customerName ?? 'Đã chọn'}
        </div>
      )}
      <CustomerQuickSearch key={resetKey} onPick={handle} allowGuest />
    </div>
  );
}
