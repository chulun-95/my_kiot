import { describe, it, expect } from 'vitest';
import * as supplierApi from '../supplier';

describe('supplier API', () => {
  it('listSuppliers returns items', async () => {
    const res = await supplierApi.listSuppliers();
    expect(res.items[0].name).toBe('NCC Acecook');
  });

  it('getSupplier returns single', async () => {
    const s = await supplierApi.getSupplier(1);
    expect(s.tax_code).toBe('0102030405');
  });

  it('createSupplier returns new supplier', async () => {
    const s = await supplierApi.createSupplier({ name: 'NCC X' });
    expect(s.id).toBe(300);
  });

  it('updateSupplier returns updated', async () => {
    const s = await supplierApi.updateSupplier(1, { name: 'Đổi tên' });
    expect(s.name).toBe('Đổi tên');
  });

  it('deleteSupplier returns message', async () => {
    const res = await supplierApi.deleteSupplier(1);
    expect(res.message).toMatch(/Đã xóa/);
  });
});
