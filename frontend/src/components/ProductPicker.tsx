import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import * as productApi from '../api/product';
import type { ProductBrief } from '../api/product';
import { formatVND } from '../utils/format';
import { toFriendlyMessage } from '../utils/errors';

interface Props {
  onPick: (product: ProductBrief) => void;
  autoFocus?: boolean;
  placeholder?: string;
}

const BARCODE_RE = /^\d{6,}$/;

export default function ProductPicker({
  onPick,
  autoFocus = false,
  placeholder = 'Quét mã vạch hoặc tìm sản phẩm...',
}: Props) {
  const [value, setValue] = useState('');
  const [items, setItems] = useState<ProductBrief[]>([]);
  const [highlight, setHighlight] = useState(0);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    setError(null);
    const q = value.trim();
    if (!q) {
      setItems([]);
      setOpen(false);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const res = await productApi.searchProducts(q, 8);
        setItems(res.items);
        setHighlight(0);
        setOpen(true);
      } catch {
        setItems([]);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [value]);

  const pick = (p: ProductBrief) => {
    onPick(p);
    setValue('');
    setItems([]);
    setOpen(false);
    setHighlight(0);
    inputRef.current?.focus();
  };

  const onKeyDown = async (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const v = value.trim();
      if (BARCODE_RE.test(v)) {
        try {
          const p = await productApi.getProductByBarcode(v);
          pick(p);
        } catch (err) {
          setError(toFriendlyMessage(err, 'Không tìm thấy mã vạch'));
        }
        return;
      }
      if (items[highlight]) pick(items[highlight]);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(items.length - 1, h + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
    } else if (e.key === 'Escape') {
      setValue('');
      setItems([]);
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        aria-label="Tìm sản phẩm hoặc quét mã vạch"
        className="w-full px-3 py-2 border border-slate-300 rounded"
      />
      {error && (
        <div role="alert" className="text-xs text-rose-600 mt-1">
          {error}
        </div>
      )}
      {open && items.length > 0 && (
        <ul
          role="listbox"
          className="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded shadow z-10 max-h-80 overflow-auto"
        >
          {items.map((p, idx) => (
            <li
              key={p.id}
              role="option"
              aria-selected={idx === highlight}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(p);
              }}
              className={`px-3 py-2 cursor-pointer text-sm flex justify-between gap-3 ${
                idx === highlight ? 'bg-slate-100' : ''
              }`}
            >
              <span>
                <span className="font-medium">{p.name}</span>
                <span className="text-xs text-slate-500 ml-2 font-mono">
                  {p.sku}
                </span>
              </span>
              <span className="text-slate-700">{formatVND(p.sale_price as number)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
