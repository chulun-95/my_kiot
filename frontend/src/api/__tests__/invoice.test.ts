import { describe, it, expect } from 'vitest';
import * as invoiceApi from '../invoice';

describe('invoice API', () => {
  it('listInvoices returns items + pagination', async () => {
    const res = await invoiceApi.listInvoices({ page: 1, limit: 20 });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items[0].code).toBe('HD20260523-001');
    expect(res.pagination.total).toBe(2);
  });

  it('listInvoices honors EMPTY filter', async () => {
    const res = await invoiceApi.listInvoices({
      status: 'EMPTY' as 'DRAFT',
    });
    expect(res.items).toEqual([]);
  });

  it('listDrafts returns drafts list', async () => {
    const res = await invoiceApi.listDrafts(true);
    expect(res.items[0].status).toBe('DRAFT');
  });

  it('getInvoice returns full detail', async () => {
    const inv = await invoiceApi.getInvoice(11);
    expect(inv.id).toBe(11);
    expect(inv.items[0].product_name).toBe('Mì tôm Hảo Hảo');
    expect(inv.payments[0].method).toBe('CASH');
  });

  it('createDraft returns new DRAFT invoice', async () => {
    const inv = await invoiceApi.createDraft({
      items: [{ product_id: 1, quantity: 2, unit_price: 5000 }],
    });
    expect(inv.status).toBe('DRAFT');
    expect(Number(inv.subtotal)).toBe(10000);
  });

  it('updateDraft returns updated invoice', async () => {
    const inv = await invoiceApi.updateDraft(200, {
      items: [{ product_id: 2, quantity: 3, unit_price: 4000 }],
    });
    expect(Number(inv.subtotal)).toBe(12000);
  });

  it('completeInvoice returns COMPLETED status with change', async () => {
    const inv = await invoiceApi.completeInvoice(1, {
      payments: [{ method: 'CASH', amount: 120000 }],
    });
    expect(inv.status).toBe('COMPLETED');
    expect(Number(inv.change_amount)).toBe(20000);
  });

  it('completeInvoice returns INSUFFICIENT_STOCK for id 9999', async () => {
    await expect(
      invoiceApi.completeInvoice(9999, {
        payments: [{ method: 'CASH', amount: 1000 }],
      }),
    ).rejects.toMatchObject({
      response: { status: 400 },
    });
  });

  it('cancelInvoice returns CANCELLED status', async () => {
    const inv = await invoiceApi.cancelInvoice(1, 'lỗi nhập');
    expect(inv.status).toBe('CANCELLED');
    expect(inv.cancel_reason).toBe('lỗi nhập');
  });
});
