import { describe, it, expect } from 'vitest';
import * as customerApi from '../customer';

describe('customer API', () => {
  it('listCustomers returns items', async () => {
    const res = await customerApi.listCustomers();
    expect(res.items[0].name).toBe('Nguyễn Văn A');
  });

  it('getCustomer returns customer + recent_orders', async () => {
    const res = await customerApi.getCustomer(1);
    expect(res.customer.id).toBe(1);
    expect(res.recent_orders[0].code).toBe('HD20260520-001');
  });

  it('createCustomer returns new customer', async () => {
    const c = await customerApi.createCustomer({ name: 'KH mới', phone: '0907777777' });
    expect(c.id).toBe(200);
    expect(c.phone).toBe('0907777777');
  });

  it('updateCustomer returns updated customer', async () => {
    const c = await customerApi.updateCustomer(1, { name: 'Đổi' });
    expect(c.name).toBe('Đổi');
  });

  it('deleteCustomer returns message', async () => {
    const res = await customerApi.deleteCustomer(1);
    expect(res.message).toMatch(/Đã xóa/);
  });

  it('getCustomerByPhone returns on hit', async () => {
    const c = await customerApi.getCustomerByPhone('0901234567');
    expect(c.id).toBe(50);
  });

  it('getCustomerByPhone surfaces 404', async () => {
    await expect(
      customerApi.getCustomerByPhone('0999999999'),
    ).rejects.toMatchObject({ response: { status: 404 } });
  });
});
