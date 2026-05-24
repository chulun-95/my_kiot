import { formatVND } from '../../utils/format';
import { computeCartLineTotal, type CartItem } from '../../stores/posStore';
import MoneyInput from '../../components/MoneyInput';
import QtyInput from '../../components/QtyInput';

interface Props {
  item: CartItem;
  onChangeQty: (qty: number) => void;
  onChangeDiscount: (d: number) => void;
  onRemove: () => void;
}

export default function CartLine({
  item,
  onChangeQty,
  onChangeDiscount,
  onRemove,
}: Props) {
  const lineTotal = computeCartLineTotal(item);
  return (
    <tr className="border-t border-slate-100">
      <td className="px-2 py-2 font-mono text-xs">{item.product_sku}</td>
      <td className="px-2 py-2">
        <div>{item.product_name}</div>
        <div className="text-xs text-slate-500">{item.unit}</div>
      </td>
      <td className="px-2 py-2 text-right">
        <QtyInput
          value={item.quantity}
          onChange={onChangeQty}
          className="w-20 px-2 py-1 border border-slate-300 rounded text-right"
          aria-label={`Số lượng ${item.product_name}`}
        />
      </td>
      <td className="px-2 py-2 text-right">{formatVND(item.unit_price)}</td>
      <td className="px-2 py-2 text-right">
        <div className="w-32 inline-block">
          <MoneyInput
            value={item.discount_amount}
            onChange={(v) => onChangeDiscount(v)}
            className="w-full px-2 py-1 border border-slate-300 rounded"
            aria-label={`Giảm giá ${item.product_name}`}
          />
        </div>
      </td>
      <td className="px-2 py-2 text-right font-medium">{formatVND(lineTotal)}</td>
      <td className="px-2 py-2 text-right">
        <button
          onClick={onRemove}
          className="px-2 py-1 rounded border border-rose-300 text-rose-700 text-xs"
          aria-label={`Xóa ${item.product_name}`}
        >
          Xóa
        </button>
      </td>
    </tr>
  );
}
