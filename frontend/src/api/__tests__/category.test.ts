import { describe, it, expect } from 'vitest';
import * as categoryApi from '../category';

describe('category API', () => {
  it('listCategories returns tree', async () => {
    const res = await categoryApi.listCategories();
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items[0].children.length).toBeGreaterThan(0);
  });

  it('createCategory returns new node', async () => {
    const c = await categoryApi.createCategory({ name: 'Mới' });
    expect(c.id).toBe(100);
    expect(c.depth).toBe(1);
  });

  it('createCategory under parent has depth=2', async () => {
    const c = await categoryApi.createCategory({ name: 'Con', parent_id: 1 });
    expect(c.depth).toBe(2);
  });

  it('updateCategory returns updated node', async () => {
    const c = await categoryApi.updateCategory(1, { name: 'Đổi tên' });
    expect(c.name).toBe('Đổi tên');
  });

  it('deleteCategory returns message', async () => {
    const res = await categoryApi.deleteCategory(1);
    expect(res.message).toMatch(/Đã xóa/);
  });
});
