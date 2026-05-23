import CustomerQuickSearch from '../../components/CustomerQuickSearch';
import type { CustomerResponse } from '../../api/customer';

interface Props {
  customerId: number | null;
  customerName: string | null;
  onChange: (id: number | null, name: string | null) => void;
}

export default function CustomerSelectBox({
  customerId,
  customerName,
  onChange,
}: Props) {
  const handle = (c: CustomerResponse | null) => {
    if (c) onChange(c.id, c.name);
    else onChange(null, null);
  };

  return (
    <div className="space-y-2">
      <div className="text-sm text-slate-700">
        {customerId
          ? `Khách: ${customerName ?? 'Đã chọn'}`
          : 'Khách lẻ (không gán)'}
      </div>
      <CustomerQuickSearch onPick={handle} allowGuest />
    </div>
  );
}
