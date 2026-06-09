import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import * as goodsReceiptApi from '../../api/goodsReceipt';
import { RECEIPT_PAYMENT_METHOD_LABELS } from '../../api/goodsReceipt';
import type { GoodsReceiptResponse } from '../../api/goodsReceipt';
import { useAuthStore } from '../../stores/authStore';
import { formatVND, formatDate, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function GoodsReceiptDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const role = useAuthStore((s) => s.user?.role);
  const [receipt, setReceipt] = useState<GoodsReceiptResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const r = await goodsReceiptApi.get(Number(id));
      setReceipt(r);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const onComplete = async () => {
    if (!receipt) return;
    // Nhập nợ (trả thiếu) bắt buộc có NCC — nếu không công nợ phải trả sẽ không
    // được thống kê. Chặn sớm ở FE, backend cũng chặn (DEBT_REQUIRES_SUPPLIER).
    if (Number(receipt.paid_amount) < Number(receipt.total) && receipt.supplier_id == null) {
      setError(
        'Nhập nợ phải chọn nhà cung cấp — không thể ghi nợ khi chưa có NCC. ' +
          'Hãy sửa phiếu để chọn NCC hoặc thanh toán đủ.',
      );
      return;
    }
    if (!window.confirm('Bạn chắc chắn muốn hoàn tất phiếu nhập này?')) return;
    setBusy(true);
    setError(null);
    try {
      await goodsReceiptApi.complete(receipt.id);
      await load();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onCancel = async () => {
    if (!receipt) return;
    const reason = window.prompt('Lý do hủy phiếu:');
    if (reason === null) return;
    setBusy(true);
    setError(null);
    try {
      await goodsReceiptApi.cancel(receipt.id, reason || undefined);
      await load();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="text-slate-500">Đang tải...</div>;
  }
  if (!receipt) {
    return (
      <div className="space-y-2">
        <div className="text-rose-600">{error ?? 'Không tìm thấy phiếu nhập'}</div>
        <button
          onClick={() => navigate('/goods-receipts')}
          className="px-3 py-2 rounded border border-slate-300"
        >
          ← Quay lại
        </button>
      </div>
    );
  }

  const canComplete = receipt.status === 'DRAFT';
  const canCancel =
    receipt.status === 'DRAFT' ||
    (receipt.status === 'COMPLETED' && role === 'OWNER');

  const statusLabel =
    receipt.status === 'COMPLETED'
      ? 'Hoàn tất'
      : receipt.status === 'CANCELLED'
      ? 'Đã hủy'
      : 'Nháp';

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/goods-receipts" className="text-sm text-slate-600 hover:underline">
            ← Quay lại
          </Link>
          <h1 className="text-2xl font-semibold mt-1">Phiếu nhập {receipt.code}</h1>
        </div>
        <div className="flex gap-2">
          {canComplete && (
            <button
              onClick={onComplete}
              disabled={busy}
              className="px-3 py-2 rounded bg-emerald-600 text-white disabled:opacity-50"
            >
              {busy ? 'Đang xử lý...' : 'Hoàn tất'}
            </button>
          )}
          {canCancel && (
            <button
              onClick={onCancel}
              disabled={busy}
              className="px-3 py-2 rounded bg-rose-600 text-white disabled:opacity-50"
            >
              Hủy phiếu
            </button>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded p-4 grid grid-cols-2 gap-y-2 gap-x-4 text-sm">
        <div className="text-slate-600">Trạng thái</div>
        <div>{statusLabel}</div>
        <div className="text-slate-600">NCC</div>
        <div>{receipt.supplier_name ?? '-'}</div>
        <div className="text-slate-600">Tạo lúc</div>
        <div>{formatDate(receipt.created_at)}</div>
        <div className="text-slate-600">Hoàn tất lúc</div>
        <div>{formatDate(receipt.completed_at)}</div>
        <div className="text-slate-600">Tổng tiền</div>
        <div className="font-semibold">{formatVND(receipt.total as number)}</div>
        <div className="text-slate-600">Đã thanh toán</div>
        <div>
          {formatVND(receipt.paid_amount as number)}
          {Number(receipt.paid_amount) > 0 && receipt.payment_method && (
            <span className="text-slate-500">
              {' '}({RECEIPT_PAYMENT_METHOD_LABELS[receipt.payment_method]})
            </span>
          )}
        </div>
        <div className="text-slate-600">Ghi chú</div>
        <div>{receipt.note ?? '-'}</div>
      </div>

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Tên SP</th>
              <th className="px-3 py-2 text-right">Số lượng</th>
              <th className="px-3 py-2 text-right">Giá nhập</th>
              <th className="px-3 py-2 text-right">Thành tiền</th>
            </tr>
          </thead>
          <tbody>
            {receipt.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                  Phiếu trống
                </td>
              </tr>
            ) : (
              receipt.items.map((it) => (
                <tr key={it.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{it.product_sku ?? '-'}</td>
                  <td className="px-3 py-2">{it.product_name ?? `SP #${it.product_id}`}</td>
                  <td className="px-3 py-2 text-right">{formatQty(it.quantity as number)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(it.cost_price as number)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(it.line_total as number)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
