import { describe, it, expect } from 'vitest';
import * as productApi from '../product';

describe('product API', () => {
  it('listProducts returns items + pagination', async () => {
    const res = await productApi.listProducts({ page: 1, limit: 20 });
    expect(res.items[0].sku).toBe('SP000001');
    expect(res.pagination.total).toBe(1);
  });

  it('listProducts forwards search param (empty result)', async () => {
    const res = await productApi.listProducts({ search: 'EMPTY' });
    expect(res.items).toEqual([]);
  });

  it('getProduct returns single product', async () => {
    const p = await productApi.getProduct(1);
    expect(p.id).toBe(1);
    expect(p.name).toBe('Mì tôm Hảo Hảo');
  });

  it('createProduct surfaces 409 DUPLICATE_SKU', async () => {
    await expect(
      productApi.createProduct({ name: 'X', sku: 'DUP' }),
    ).rejects.toMatchObject({ response: { status: 409 } });
  });

  it('createProduct returns created entity', async () => {
    const p = await productApi.createProduct({ name: 'Sản phẩm mới' });
    expect(p.id).toBe(99);
    expect(p.name).toBe('Sản phẩm mới');
  });

  it('updateProduct returns updated entity', async () => {
    const p = await productApi.updateProduct(1, { name: 'Đổi tên' });
    expect(p.name).toBe('Đổi tên');
  });

  it('deleteProduct returns message', async () => {
    const res = await productApi.deleteProduct(1);
    expect(res.message).toMatch(/ngừng/i);
  });

  it('searchProducts returns brief items', async () => {
    const res = await productApi.searchProducts('mì', 5);
    expect(res.items[0].name).toContain('mì');
  });

  it('getProductByBarcode returns brief on hit', async () => {
    const p = await productApi.getProductByBarcode('8934567890123');
    expect(p.id).toBe(11);
  });

  it('getProductByBarcode raises 404 on miss', async () => {
    await expect(
      productApi.getProductByBarcode('0000000000000'),
    ).rejects.toMatchObject({ response: { status: 404 } });
  });
});
