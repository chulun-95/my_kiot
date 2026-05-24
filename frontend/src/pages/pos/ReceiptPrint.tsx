import { useEffect } from 'react';
import type { InvoiceResponse } from '../../api/invoice';
import type { Tenant } from '../../stores/authStore';
import { formatVND, formatDate, formatQty } from '../../utils/format';

interface Props {
  invoice: InvoiceResponse;
  tenant: Tenant | null;
  onClose: () => void;
}

export default function ReceiptPrint({ invoice, tenant, onClose }: Props) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === 'Enter' || e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        window.print();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-label="In hóa đơn"
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center print-overlay"
    >
      <style>
        {`
        @media print {
          body * { visibility: hidden; }
          .receipt, .receipt * { visibility: visible; }
          .receipt {
            position: absolute;
            left: 0;
            top: 0;
            width: 80mm;
            padding: 4mm;
            font-family: monospace;
            font-size: 11px;
            color: #000;
          }
          .print-overlay { background: none !important; }
          .no-print { display: none !important; }
        }
        `}
      </style>
      <div className="bg-white rounded shadow-lg w-full max-w-md p-4 space-y-3">
        <div className="receipt text-xs">
          <div className="text-center font-semibold text-sm">
            {tenant?.name ?? 'my_kiot POS'}
          </div>
          <div className="text-center text-[10px] text-slate-600">
            HÓA ĐƠN BÁN HÀNG
          </div>
          <div className="mt-2 flex justify-between">
            <span>Mã:</span>
            <span className="font-mono">{invoice.code}</span>
          </div>
          <div className="flex justify-between">
            <span>Ngày:</span>
            <span>{formatDate(invoice.completed_at || invoice.created_at)}</span>
          </div>
          <div className="flex justify-between">
            <span>Thu ngân:</span>
            <span>{invoice.cashier_name ?? '-'}</span>
          </div>
          <div className="flex justify-between">
            <span>Khách:</span>
            <span>{invoice.customer_name ?? 'Khách lẻ'}</span>
          </div>
          <hr className="my-2 border-slate-300" />
          <table className="w-full">
            <thead>
              <tr className="text-left">
                <th className="py-1">SP</th>
                <th className="py-1 text-right">SL</th>
                <th className="py-1 text-right">T.tiền</th>
              </tr>
            </thead>
            <tbody>
              {invoice.items.map((it) => (
                <tr key={it.id} className="align-top">
                  <td className="py-1">
                    <div>{it.product_name}</div>
                    <div className="text-[10px] text-slate-500">
                      {formatVND(it.unit_price)} / {it.unit ?? ''}
                    </div>
                  </td>
                  <td className="py-1 text-right">{formatQty(it.quantity)}</td>
                  <td className="py-1 text-right">{formatVND(it.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <hr className="my-2 border-slate-300" />
          <div className="flex justify-between">
            <span>Tạm tính</span>
            <span>{formatVND(invoice.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span>Giảm giá</span>
            <span>{formatVND(invoice.discount_amount)}</span>
          </div>
          <div className="flex justify-between font-semibold text-sm">
            <span>Tổng</span>
            <span>{formatVND(invoice.total)}</span>
          </div>
          {invoice.payments.map((p) => (
            <div key={p.id} className="flex justify-between text-[10px]">
              <span>{p.method}</span>
              <span>{formatVND(p.amount)}</span>
            </div>
          ))}
          {Number(invoice.change_amount) > 0 && (
            <div className="flex justify-between">
              <span>Tiền thừa</span>
              <span>{formatVND(invoice.change_amount)}</span>
            </div>
          )}
          <div className="text-center mt-3 text-[10px]">
            Cám ơn quý khách!
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 no-print">
          <span className="text-[11px] text-slate-500">
            Enter/P: In · Esc: Đóng
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => window.print()}
              className="px-3 py-2 rounded bg-slate-900 text-white"
            >
              In ngay
            </button>
            <button
              onClick={onClose}
              className="px-3 py-2 rounded border border-slate-300"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
