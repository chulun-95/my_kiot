import { describe, it, expect } from 'vitest';
import * as inventoryApi from '../inventory';

describe('inventory API', () => {
  it('list returns inventory items + pagination', async () => {
    const res = await inventoryApi.list({ page: 1, limit: 20 });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items[0].product_sku).toBe('SP000001');
  });

  it('list forwards search "EMPTY"', async () => {
    const res = await inventoryApi.list({ search: 'EMPTY' });
    expect(res.items).toEqual([]);
  });

  it('getLowStock returns flagged items', async () => {
    const res = await inventoryApi.getLowStock();
    // API sắp xếp theo tồn tăng dần (OUT_OF_STOCK trước), nên tra theo SKU
    // thay vì giả định vị trí phần tử đầu.
    const item = res.items.find((i) => i.product_sku === 'SP000001');
    expect(item).toBeDefined();
    expect(Number(item!.quantity)).toBe(3);
  });

  it('getMovements returns kardex timeline', async () => {
    const res = await inventoryApi.getMovements(1);
    expect(res.items.length).toBe(2);
    expect(res.items[0].type).toBe('RECEIPT');
    expect(res.items[1].type).toBe('SALE');
  });

  it('createAdjustment returns delta', async () => {
    const res = await inventoryApi.createAdjustment({
      items: [{ product_id: 1, new_quantity: 42, reason: 'Kiểm kê' }],
    });
    expect(res.items[0].new_quantity).toBe(42);
    expect(Number(res.items[0].delta)).toBe(32);
  });

  it('listAdjustments returns paginated list', async () => {
    const res = await inventoryApi.listAdjustments({ page: 1, limit: 50 });
    expect(res.items[0].product_sku).toBe('SP000001');
    expect(res.pagination.total).toBe(1);
  });
});
