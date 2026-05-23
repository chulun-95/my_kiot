import { describe, it, expect } from 'vitest';
import * as receiptApi from '../goodsReceipt';

describe('goodsReceipt API', () => {
  it('list returns items + pagination', async () => {
    const res = await receiptApi.list({ page: 1, limit: 20 });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items[0].code).toBe('NK20260520-001');
    expect(res.pagination.total).toBe(2);
  });

  it('list forwards status filter (empty result)', async () => {
    const res = await receiptApi.list({ status: 'EMPTY' as 'DRAFT' });
    expect(res.items).toEqual([]);
  });

  it('get returns a single completed receipt with items', async () => {
    const r = await receiptApi.get(1);
    expect(r.id).toBe(1);
    expect(r.status).toBe('COMPLETED');
    expect(r.items[0].product_name).toBe('Mì tôm Hảo Hảo');
  });

  it('get returns a draft receipt empty items', async () => {
    const r = await receiptApi.get(2);
    expect(r.status).toBe('DRAFT');
  });

  it('create returns new draft receipt with computed total', async () => {
    const r = await receiptApi.create({
      supplier_id: null,
      items: [{ product_id: 1, quantity: 10, cost_price: 1000 }],
      paid_amount: 0,
    });
    expect(r.status).toBe('DRAFT');
    expect(Number(r.total)).toBe(10000);
    expect(r.items[0].product_id).toBe(1);
  });

  it('update returns updated draft', async () => {
    const r = await receiptApi.update(2, {
      items: [{ product_id: 2, quantity: 5, cost_price: 2000 }],
    });
    expect(Number(r.total)).toBe(10000);
  });

  it('complete returns COMPLETED status', async () => {
    const r = await receiptApi.complete(2);
    expect(r.status).toBe('COMPLETED');
  });

  it('cancel returns CANCELLED status', async () => {
    const r = await receiptApi.cancel(1, 'sai số liệu');
    expect(r.status).toBe('CANCELLED');
  });
});
