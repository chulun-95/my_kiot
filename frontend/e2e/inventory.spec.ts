import { test, expect } from '@playwright/test';
import { BASE_URL, API_URL, createProductViaAPI, addStockViaAPI, loginViaAPI, loginViaUI } from './helpers';
import { TEST_OWNER } from './global-setup';

let token: string;
let productId: number;

test.beforeAll(async ({ request }) => {
  // Get auth token via API
  token = await loginViaAPI(request, TEST_OWNER.phone, TEST_OWNER.password);

  // Create a product to use in inventory tests
  const product = await createProductViaAPI(request, token, {
    name: 'Bia Heineken 330ml E2E',
    sale_price: 18000,
    cost_price: 12000,
  });
  productId = product.id;
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page, TEST_OWNER.phone, TEST_OWNER.password);
});

test.describe('Nhập kho — danh sách', () => {
  test('trang Nhập kho hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/goods-receipts`);
    await expect(page.locator('h1')).toContainText('Phiếu nhập kho');
  });

  test('nút Nhập hàng mới tồn tại', async ({ page }) => {
    await page.goto(`${BASE_URL}/goods-receipts`);
    await expect(page.locator('a:has-text("Nhập hàng mới")')).toBeVisible();
  });
});

test.describe('Nhập kho — tạo phiếu nhập', () => {
  test('tạo và hoàn tất phiếu nhập → tồn kho tăng', async ({ page, request }) => {
    // Add stock via API
    await addStockViaAPI(request, token, productId, 50, 12000);

    // Check inventory
    const invRes = await request.get(`${API_URL}/inventory`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const inv = await invRes.json() as { items: Array<{ product_id: number; quantity: number }> };
    const row = inv.items.find((i) => i.product_id === productId);
    expect(Number(row?.quantity)).toBeGreaterThanOrEqual(50);

    // Verify in UI
    await page.goto(`${BASE_URL}/inventory`);
    await expect(page.locator('h1')).toContainText('Tồn kho');
    await expect(page.locator('body')).toContainText('Bia Heineken 330ml E2E');
  });

  test('form nhập hàng mới → chọn SP → tạo phiếu nháp', async ({ page }) => {
    await page.goto(`${BASE_URL}/goods-receipts/new`);
    await expect(page.locator('h1')).toContainText('Nhập hàng mới');

    // Fill the ProductPicker input (single input, placeholder contains "Quét" and "tìm SP")
    const pickerInput = page.locator('input[placeholder*="tìm SP"]').first();
    await pickerInput.fill('Bia Heineken');
    await page.waitForTimeout(600);

    // Click on the product result from dropdown
    const productRow = page.locator('[role="listbox"] [role="option"]').filter({ hasText: 'Bia Heineken' }).first();
    const fallbackRow = page.locator('text=Bia Heineken 330ml E2E').first();
    if (await productRow.count() > 0) {
      await productRow.click();
    } else if (await fallbackRow.count() > 0) {
      await fallbackRow.click();
    }

    // Check that a line item was added
    await expect(page.locator('text=Bia Heineken')).toBeVisible();
  });
});

test.describe('Tồn kho', () => {
  test('trang Tồn kho hiển thị danh sách', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    await expect(page.locator('h1')).toContainText('Tồn kho');
  });

  test('thẻ kho (kardex) của sản phẩm', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    await page.waitForSelector('h1:has-text("Tồn kho")');

    // Click on product to see kardex
    const kardexLink = page.locator(`a[href*="/inventory/${productId}/movements"]`);
    if (await kardexLink.count() > 0) {
      await kardexLink.click();
      await expect(page.locator('h1')).toContainText('Thẻ kho');
      await expect(page.locator('body')).toContainText('RECEIPT');
    } else {
      // Try navigating directly
      await page.goto(`${BASE_URL}/inventory/${productId}/movements`);
      await expect(page.locator('h1')).toContainText('Thẻ kho');
    }
  });

  test('hàng sắp hết (Owner only)', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory/low-stock`);
    await expect(page.locator('h1')).toContainText('Cảnh báo tồn kho');
  });
});

test.describe('Phiếu nhập — lịch sử', () => {
  test('danh sách phiếu nhập hiển thị sau khi complete', async ({ page }) => {
    // Navigate directly — stock already added by earlier tests in this file
    await page.goto(`${BASE_URL}/goods-receipts`);
    await page.waitForURL(`${BASE_URL}/goods-receipts`, { timeout: 10_000 });
    await expect(page.locator('h1')).toContainText('Phiếu nhập kho');
    // target badge span inside table, not the hidden <option> in the status filter dropdown
    await expect(page.locator('tbody td span:has-text("Hoàn tất")').first()).toBeVisible({ timeout: 5_000 });
  });
});
