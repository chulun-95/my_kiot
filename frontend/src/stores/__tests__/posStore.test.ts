import { describe, it, expect, beforeEach } from 'vitest';
import { usePosStore } from '../posStore';
import type { ProductBrief } from '../../api/product';

const sampleProduct: ProductBrief = {
  id: 1,
  sku: 'SP000001',
  barcode: '8934567890124',
  name: 'Mì tôm Hảo Hảo',
  unit: 'gói',
  sale_price: 5000,
  cost_price: 3500,
  image_url: null,
  allow_negative: false,
  status: 'ACTIVE',
};

describe('posStore', () => {
  beforeEach(() => {
    usePosStore.getState().reset();
    usePosStore.setState({ lastCompleted: null });
  });

  it('addItem adds new line with sale_price as unit_price', () => {
    usePosStore.getState().addItem(sampleProduct);
    const items = usePosStore.getState().items;
    expect(items).toHaveLength(1);
    expect(items[0].quantity).toBe(1);
    expect(items[0].unit_price).toBe(5000);
  });

  it('addItem on duplicate increments quantity', () => {
    usePosStore.getState().addItem(sampleProduct);
    usePosStore.getState().addItem(sampleProduct);
    expect(usePosStore.getState().items[0].quantity).toBe(2);
  });

  it('updateQty / updateLineDiscount / removeItem', () => {
    usePosStore.getState().addItem(sampleProduct);
    usePosStore.getState().updateQty(1, 3.5);
    expect(usePosStore.getState().items[0].quantity).toBe(3.5);
    usePosStore.getState().updateLineDiscount(1, 500);
    expect(usePosStore.getState().items[0].discount_amount).toBe(500);
    usePosStore.getState().removeItem(1);
    expect(usePosStore.getState().items).toHaveLength(0);
  });

  it('subtotal and total math', () => {
    usePosStore.getState().addItem(sampleProduct); // 5000 x 1
    usePosStore.getState().updateQty(1, 2);
    expect(usePosStore.getState().subtotal()).toBe(10000);
    usePosStore.getState().applyDiscount(2000);
    expect(usePosStore.getState().total()).toBe(8000);
  });

  it('hold creates draft and sets draftId', async () => {
    usePosStore.getState().addItem(sampleProduct);
    const res = await usePosStore.getState().hold();
    expect(res.status).toBe('DRAFT');
    expect(usePosStore.getState().draftId).toBe(res.id);
  });

  it('hold updates existing draft when draftId is set', async () => {
    usePosStore.getState().addItem(sampleProduct);
    const first = await usePosStore.getState().hold();
    const firstId = first.id;
    usePosStore.getState().updateQty(1, 5);
    const second = await usePosStore.getState().hold();
    expect(second.id).toBe(firstId);
    expect(usePosStore.getState().draftId).toBe(firstId);
  });

  it('restore loads draft items into cart', () => {
    usePosStore.getState().restore({
      id: 70,
      code: 'HD20260523-001',
      customer_id: 1,
      customer_name: 'Khách',
      cashier_id: 1,
      cashier_name: 'Chủ',
      subtotal: 10000,
      discount_amount: 0,
      total: 10000,
      cost_total: 0,
      paid_amount: 0,
      change_amount: 0,
      status: 'DRAFT',
      note: 'ghi chú',
      completed_at: null,
      cancelled_at: null,
      cancel_reason: null,
      created_at: '2026-05-23T08:00:00Z',
      items: [
        {
          id: 1,
          product_id: 1,
          product_name: 'Mì tôm Hảo Hảo',
          product_sku: 'SP000001',
          unit: 'gói',
          quantity: 2,
          unit_price: 5000,
          cost_price: 3500,
          discount_amount: 0,
          line_total: 10000,
        },
      ],
      payments: [],
    });
    const state = usePosStore.getState();
    expect(state.draftId).toBe(70);
    expect(state.items).toHaveLength(1);
    expect(state.items[0].quantity).toBe(2);
    expect(state.customerName).toBe('Khách');
  });

  it('complete success clears cart and stores lastCompleted', async () => {
    usePosStore.getState().addItem(sampleProduct);
    // Force a draftId so completeInvoice handler returns 200
    usePosStore.setState({ draftId: 1 });
    const res = await usePosStore
      .getState()
      .complete([{ method: 'CASH', amount: 100000 }]);
    expect(res.status).toBe('COMPLETED');
    expect(usePosStore.getState().items).toHaveLength(0);
    expect(usePosStore.getState().lastCompleted?.id).toBe(res.id);
  });

  it('complete with INSUFFICIENT_STOCK sets shortages and rethrows', async () => {
    usePosStore.getState().addItem(sampleProduct);
    usePosStore.setState({ draftId: 9999 });
    await expect(
      usePosStore.getState().complete([{ method: 'CASH', amount: 100 }]),
    ).rejects.toBeDefined();
    expect(usePosStore.getState().shortages?.length).toBeGreaterThan(0);
    expect(usePosStore.getState().shortages?.[0].product_id).toBe(1);
  });
});
