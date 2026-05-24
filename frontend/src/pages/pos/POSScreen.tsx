import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { usePosStore } from '../../stores/posStore';
import * as productApi from '../../api/product';
import type { ProductBrief } from '../../api/product';
import ProductPicker from '../../components/ProductPicker';
import CartLine from './CartLine';
import CustomerSelectBox from './CustomerSelectBox';
import PaymentDialog from './PaymentDialog';
import DraftHoldList from './DraftHoldList';
import ReceiptPrint from './ReceiptPrint';
import useBarcodeListener from '../../hooks/useBarcodeListener';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import type { PaymentInput } from '../../api/invoice';
import MoneyInput from '../../components/MoneyInput';

export default function POSScreen() {
  const user = useAuthStore((s) => s.user);
  const tenant = useAuthStore((s) => s.tenant);
  const items = usePosStore((s) => s.items);
  const discount = usePosStore((s) => s.discount);
  const customerId = usePosStore((s) => s.customerId);
  const customerName = usePosStore((s) => s.customerName);
  const shortages = usePosStore((s) => s.shortages);
  const completing = usePosStore((s) => s.completing);
  const holding = usePosStore((s) => s.holding);
  const lastCompleted = usePosStore((s) => s.lastCompleted);

  const [paymentOpen, setPaymentOpen] = useState(false);
  const [draftPanelOpen, setDraftPanelOpen] = useState(false);
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [customerResetKey, setCustomerResetKey] = useState(0);

  const subtotal = usePosStore((s) => s.subtotal());
  const total = usePosStore((s) => s.total());

  const addByProduct = (p: ProductBrief) => {
    usePosStore.getState().addItem(p);
  };

  useBarcodeListener({
    enabled: !paymentOpen && !draftPanelOpen && !receiptOpen,
    onScan: async (code) => {
      try {
        const p = await productApi.getProductByBarcode(code);
        addByProduct(p);
      } catch {
        // ignore unknown barcodes
      }
    },
  });

  const onHold = async () => {
    if (items.length === 0) return;
    setPageError(null);
    try {
      await usePosStore.getState().hold();
      usePosStore.getState().reset();
    } catch (err) {
      setPageError(toFriendlyMessage(err));
    }
  };

  const onPay = () => {
    if (items.length === 0) return;
    setPageError(null);
    setPaymentOpen(true);
  };

  const onCancelCart = () => {
    usePosStore.getState().reset();
  };

  const anyModalOpen = paymentOpen || draftPanelOpen || receiptOpen;
  useKeyboardShortcuts(
    {
      F2: () => {
        const el = document.querySelector<HTMLInputElement>(
          'input[type="search"], input[placeholder*="sản phẩm"]',
        );
        el?.focus();
        if (el && typeof el.select === 'function') el.select();
      },
      F4: () => {
        if (!anyModalOpen) void onHold();
      },
      F9: () => {
        if (!anyModalOpen && items.length > 0) setPaymentOpen(true);
      },
      Escape: () => {
        if (receiptOpen) setReceiptOpen(false);
        else if (paymentOpen) setPaymentOpen(false);
        else if (draftPanelOpen) setDraftPanelOpen(false);
      },
    },
    { enabled: true },
  );

  const onComplete = async (payments: PaymentInput[], allowDebt: boolean) => {
    try {
      await usePosStore.getState().complete(payments, allowDebt);
      setPaymentOpen(false);
      setReceiptOpen(true);
      setCustomerResetKey((k) => k + 1);
    } catch (err) {
      // shortages already set on store; surface message
      setPageError(toFriendlyMessage(err));
      throw err;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <header className="h-12 px-4 flex items-center justify-between border-b border-slate-200 bg-white">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="text-sm text-slate-700 underline">
            ← Quay lại
          </Link>
          <span className="font-semibold text-slate-900">
            POS · {tenant?.name ?? 'Shop'}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span>Thu ngân: {user?.full_name ?? '-'}</span>
          <button
            onClick={() => setDraftPanelOpen(true)}
            className="px-3 py-1 rounded border border-slate-300 bg-white"
          >
            Hóa đơn treo
          </button>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
        <section className="col-span-12 md:col-span-8 flex flex-col gap-2 min-h-0">
          <div className="bg-white p-3 border border-slate-200 rounded">
            <ProductPicker
              onPick={addByProduct}
              placeholder="Quét mã vạch hoặc tìm sản phẩm để thêm vào giỏ..."
              autoFocus
            />
          </div>

          {shortages && shortages.length > 0 && (
            <div
              role="alert"
              className="bg-rose-50 border border-rose-200 rounded p-3 text-sm text-rose-800 space-y-1"
            >
              <div className="font-semibold">Tồn kho không đủ:</div>
              {shortages.map((s) => (
                <div key={s.product_id}>
                  · {s.product_name}: cần {s.need}, còn {s.have}
                </div>
              ))}
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded overflow-auto flex-1 min-h-0">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600 sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left">SKU</th>
                  <th className="px-2 py-2 text-left">Sản phẩm</th>
                  <th className="px-2 py-2 text-right">Số lượng</th>
                  <th className="px-2 py-2 text-right">Đơn giá</th>
                  <th className="px-2 py-2 text-right">Giảm</th>
                  <th className="px-2 py-2 text-right">Thành tiền</th>
                  <th className="px-2 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-3 py-10 text-center text-slate-500"
                    >
                      Giỏ trống. Quét mã hoặc tìm sản phẩm để bắt đầu.
                    </td>
                  </tr>
                ) : (
                  items.map((it) => (
                    <CartLine
                      key={it.product_id}
                      item={it}
                      onChangeQty={(q) =>
                        usePosStore.getState().updateQty(it.product_id, q)
                      }
                      onChangeDiscount={(d) =>
                        usePosStore
                          .getState()
                          .updateLineDiscount(it.product_id, d)
                      }
                      onRemove={() =>
                        usePosStore.getState().removeItem(it.product_id)
                      }
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="col-span-12 md:col-span-4 bg-white border border-slate-200 rounded p-3 flex flex-col gap-3 overflow-auto">
          <CustomerSelectBox
            customerId={customerId}
            customerName={customerName}
            onChange={(id, name) =>
              usePosStore.getState().setCustomer(id, name)
            }
            resetKey={customerResetKey}
          />

          <div className="space-y-2 border-t border-slate-100 pt-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Tạm tính</span>
              <span>{formatVND(subtotal)}</span>
            </div>
            <div className="flex items-center justify-between text-sm gap-2">
              <span className="text-slate-600">Giảm hóa đơn</span>
              <div className="w-36">
                <MoneyInput
                  value={discount}
                  onChange={(v) => usePosStore.getState().applyDiscount(v)}
                  className="w-full px-2 py-1 border border-slate-300 rounded"
                  aria-label="Giảm giá toàn hóa đơn"
                />
              </div>
            </div>
            <div className="flex justify-between text-base font-semibold">
              <span>Tổng</span>
              <span>{formatVND(total)}</span>
            </div>
          </div>

          {pageError && (
            <div role="alert" className="text-sm text-rose-600">
              {pageError}
            </div>
          )}

          <div className="flex flex-col gap-2 mt-auto">
            <button
              onClick={onPay}
              disabled={items.length === 0 || completing}
              className="px-3 py-3 rounded bg-emerald-700 text-white text-lg font-semibold disabled:opacity-50"
            >
              {completing ? 'Đang xử lý...' : 'Thanh toán'}
            </button>
            <button
              onClick={onHold}
              disabled={items.length === 0 || holding}
              className="px-3 py-2 rounded border border-slate-300 disabled:opacity-50"
            >
              {holding ? 'Đang giữ...' : 'Giữ hóa đơn'}
            </button>
            <button
              onClick={onCancelCart}
              disabled={items.length === 0}
              className="px-3 py-2 rounded border border-rose-300 text-rose-700 disabled:opacity-50"
            >
              Hủy giỏ
            </button>
          </div>
        </aside>
      </div>

      <PaymentDialog
        open={paymentOpen}
        total={total}
        onClose={() => setPaymentOpen(false)}
        onComplete={onComplete}
      />

      {draftPanelOpen && (
        <DraftHoldList
          onRestore={(inv) => {
            usePosStore.getState().restore(inv);
            setDraftPanelOpen(false);
          }}
          onClose={() => setDraftPanelOpen(false)}
        />
      )}

      {receiptOpen && lastCompleted && (
        <ReceiptPrint
          invoice={lastCompleted}
          tenant={tenant}
          onClose={() => setReceiptOpen(false)}
        />
      )}
    </div>
  );
}
