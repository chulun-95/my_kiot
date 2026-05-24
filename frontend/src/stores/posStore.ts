import { create } from 'zustand';
import * as invoiceApi from '../api/invoice';
import type {
  InvoiceCompletePayload,
  InvoiceResponse,
  PaymentInput,
} from '../api/invoice';
import type { ProductBrief } from '../api/product';

export interface CartItem {
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string;
  quantity: number;
  unit_price: number;
  discount_amount: number;
}

export interface Shortage {
  product_id: number;
  product_name: string;
  need: string;
  have: string;
}

interface AxiosLikeError {
  response?: {
    status?: number;
    data?: {
      error?: {
        code?: string;
        details?: { shortages?: Shortage[] };
      };
    };
  };
}

interface PosState {
  draftId: number | null;
  customerId: number | null;
  customerName: string | null;
  items: CartItem[];
  discount: number;
  note: string;
  shortages: Shortage[] | null;
  completing: boolean;
  holding: boolean;
  lastCompleted: InvoiceResponse | null;
  reset: () => void;
  setCustomer: (id: number | null, name: string | null) => void;
  addItem: (product: ProductBrief) => void;
  updateQty: (productId: number, qty: number) => void;
  updateLineDiscount: (productId: number, d: number) => void;
  removeItem: (productId: number) => void;
  applyDiscount: (d: number) => void;
  setNote: (n: string) => void;
  clearShortages: () => void;
  hold: () => Promise<InvoiceResponse>;
  restore: (draft: InvoiceResponse) => void;
  complete: (
    payments: PaymentInput[],
    allowDebt?: boolean,
    payInFull?: boolean,
  ) => Promise<InvoiceResponse>;
  subtotal: () => number;
  total: () => number;
}

const initial = {
  draftId: null as number | null,
  customerId: null as number | null,
  customerName: null as string | null,
  items: [] as CartItem[],
  discount: 0,
  note: '',
  shortages: null as Shortage[] | null,
  completing: false,
  holding: false,
  lastCompleted: null as InvoiceResponse | null,
};

function computeLineTotal(item: CartItem): number {
  const raw = item.quantity * item.unit_price - item.discount_amount;
  return raw < 0 ? 0 : raw;
}

export const usePosStore = create<PosState>((set, get) => ({
  ...initial,

  reset: () =>
    set({
      draftId: null,
      customerId: null,
      customerName: null,
      items: [],
      discount: 0,
      note: '',
      shortages: null,
    }),

  setCustomer: (id, name) => set({ customerId: id, customerName: name }),

  addItem: (product) => {
    const items = [...get().items];
    const idx = items.findIndex((i) => i.product_id === product.id);
    if (idx >= 0) {
      items[idx] = { ...items[idx], quantity: items[idx].quantity + 1 };
    } else {
      items.push({
        product_id: product.id,
        product_name: product.name,
        product_sku: product.sku,
        unit: product.unit || 'cái',
        quantity: 1,
        unit_price: Number(product.sale_price ?? 0),
        discount_amount: 0,
      });
    }
    set({ items });
  },

  updateQty: (productId, qty) => {
    const items = get().items.map((i) =>
      i.product_id === productId ? { ...i, quantity: Math.max(0, qty) } : i,
    );
    set({ items });
  },

  updateLineDiscount: (productId, d) => {
    const items = get().items.map((i) =>
      i.product_id === productId
        ? { ...i, discount_amount: Math.max(0, d) }
        : i,
    );
    set({ items });
  },

  removeItem: (productId) => {
    set({ items: get().items.filter((i) => i.product_id !== productId) });
  },

  applyDiscount: (d) => set({ discount: Math.max(0, d) }),

  setNote: (n) => set({ note: n }),

  clearShortages: () => set({ shortages: null }),

  hold: async () => {
    const { draftId, customerId, items, discount, note } = get();
    const payload = {
      customer_id: customerId,
      items: items.map((i) => ({
        product_id: i.product_id,
        quantity: i.quantity,
        unit_price: i.unit_price,
        discount_amount: i.discount_amount,
      })),
      discount_amount: discount,
      note: note || null,
    };
    set({ holding: true });
    try {
      const res = draftId
        ? await invoiceApi.updateDraft(draftId, payload)
        : await invoiceApi.createDraft(payload);
      set({ draftId: res.id });
      return res;
    } finally {
      set({ holding: false });
    }
  },

  restore: (draft) => {
    const items: CartItem[] = draft.items.map((it) => ({
      product_id: it.product_id,
      product_name: it.product_name,
      product_sku: it.product_sku,
      unit: it.unit ?? 'cái',
      quantity: Number(it.quantity),
      unit_price: Number(it.unit_price),
      discount_amount: Number(it.discount_amount),
    }));
    set({
      draftId: draft.id,
      customerId: draft.customer_id,
      customerName: draft.customer_name,
      items,
      discount: Number(draft.discount_amount),
      note: draft.note ?? '',
      shortages: null,
    });
  },

  complete: async (payments, allowDebt = false, payInFull = false) => {
    set({ completing: true, shortages: null });
    try {
      // Luôn sync draft với backend trước khi complete:
      //  - Đảm bảo backend có items/discount mới nhất (vd: sửa giỏ sau khi restore).
      //  - Lấy invoice.total chính chủ để dùng cho pay-in-full (không tin FE total).
      const draft = await get().hold();
      const draftId = draft.id;

      let finalPayments = payments;
      if (payInFull) {
        const method = payments[0]?.method ?? 'CASH';
        const backendTotal = Number(draft.total);
        finalPayments =
          backendTotal > 0 ? [{ method, amount: backendTotal }] : [];
      }

      const payload: InvoiceCompletePayload = {
        payments: finalPayments,
        allow_debt: allowDebt,
      };
      try {
        const res = await invoiceApi.completeInvoice(draftId, payload);
        set({ lastCompleted: res });
        // clear cart but keep lastCompleted for receipt
        set({
          draftId: null,
          customerId: null,
          customerName: null,
          items: [],
          discount: 0,
          note: '',
          shortages: null,
        });
        return res;
      } catch (err) {
        const ax = err as AxiosLikeError;
        const code = ax?.response?.data?.error?.code;
        if (code === 'INSUFFICIENT_STOCK') {
          const shortages = ax?.response?.data?.error?.details?.shortages ?? [];
          set({ shortages });
        }
        throw err;
      }
    } finally {
      set({ completing: false });
    }
  },

  subtotal: () => get().items.reduce((s, i) => s + computeLineTotal(i), 0),
  total: () => {
    const subtotal = get().items.reduce((s, i) => s + computeLineTotal(i), 0);
    return Math.max(0, subtotal - get().discount);
  },
}));

export function computeCartLineTotal(item: CartItem): number {
  return computeLineTotal(item);
}
