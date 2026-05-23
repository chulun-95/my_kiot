import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as invoiceApi from '../../api/invoice';
import type { InvoiceResponse } from '../../api/invoice';
import { useAuthStore } from '../../stores/authStore';
import { formatVND, formatDate, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const inv = await invoiceApi.getInvoice(Number(id));
      setInvoice(inv);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) return <div className="text-sm text-slate-500">Đang tải...</div>;
  if (error)
    return (
      <div role="alert" className="text-sm text-rose-600">
        {error}
      </div>
    );
  if (!invoice) return null;

  const canCancel = (() => {
    if (!user) return false;
    if (invoice.status === 'CANCELLED') return false;
    if (user.role === 'OWNER') return true;
    return (
      invoice.status === 'DRAFT' && invoice.cashier_id === user.id
    );
  })();

  const onCancel = async () => {
    const reason = window.prompt('Lý do hủy?') ?? '';
    setCancelling(true);
    try {
      await invoiceApi.cancelInvoice(invoice.id, reason);
      await load();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold font-mono">{invoice.code}</h1>
          <div className="text-sm text-slate-600">
            Trạng thái: {invoice.status}
            {invoice.completed_at && ` · Hoàn tất ${formatDate(invoice.completed_at)}`}
            {invoice.cancelled_at && ` · Đã hủy ${formatDate(invoice.cancelled_at)}`}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => window.print()}
            className="px-3 py-2 rounded border border-slate-300"
          >
            In
          </button>
          {canCancel && (
            <button
              onClick={onCancel}
              disabled={cancelling}
              className="px-3 py-2 rounded bg-rose-700 text-white disabled:opacity-50"
            >
              {cancelling ? 'Đang hủy...' : 'Hủy hóa đơn'}
            </button>
          )}
          <button
            onClick={() => navigate('/invoices')}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Quay lại
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4 text-sm space-y-1">
        <div>Khách hàng: {invoice.customer_name ?? 'Khách lẻ'}</div>
        <div>Thu ngân: {invoice.cashier_name ?? '-'}</div>
        {invoice.cancel_reason && (
          <div className="text-rose-700">Lý do hủy: {invoice.cancel_reason}</div>
        )}
      </div>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Sản phẩm</th>
              <th className="px-3 py-2 text-right">SL</th>
              <th className="px-3 py-2 text-right">Đơn giá</th>
              <th className="px-3 py-2 text-right">Giảm</th>
              <th className="px-3 py-2 text-right">Thành tiền</th>
            </tr>
          </thead>
          <tbody>
            {invoice.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono text-xs">{it.product_sku}</td>
                <td className="px-3 py-2">{it.product_name}</td>
                <td className="px-3 py-2 text-right">{formatQty(it.quantity)}</td>
                <td className="px-3 py-2 text-right">{formatVND(it.unit_price)}</td>
                <td className="px-3 py-2 text-right">{formatVND(it.discount_amount)}</td>
                <td className="px-3 py-2 text-right">{formatVND(it.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4 text-sm space-y-1 max-w-md ml-auto">
        <div className="flex justify-between">
          <span>Tạm tính</span>
          <span>{formatVND(invoice.subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span>Giảm giá</span>
          <span>{formatVND(invoice.discount_amount)}</span>
        </div>
        <div className="flex justify-between font-semibold text-base">
          <span>Tổng</span>
          <span>{formatVND(invoice.total)}</span>
        </div>
        <div className="flex justify-between">
          <span>Đã trả</span>
          <span>{formatVND(invoice.paid_amount)}</span>
        </div>
        {Number(invoice.change_amount) > 0 && (
          <div className="flex justify-between text-emerald-700">
            <span>Tiền thừa</span>
            <span>{formatVND(invoice.change_amount)}</span>
          </div>
        )}
      </div>

      {invoice.payments.length > 0 && (
        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Phương thức</th>
                <th className="px-3 py-2 text-right">Số tiền</th>
                <th className="px-3 py-2 text-left">Thời gian</th>
              </tr>
            </thead>
            <tbody>
              {invoice.payments.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{p.method}</td>
                  <td className="px-3 py-2 text-right">{formatVND(p.amount)}</td>
                  <td className="px-3 py-2">{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
