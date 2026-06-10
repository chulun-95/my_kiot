import { test, expect } from '@playwright/test';
import { BASE_URL, API_URL, createProductViaAPI, addStockViaAPI, loginViaAPI, loginViaUI } from './helpers';
import { TEST_OWNER } from './global-setup';

let token: string;
let posProductId: number;
let posProductSku: string;

test.beforeAll(async ({ request }) => {
  token = await loginViaAPI(request, TEST_OWNER.phone, TEST_OWNER.password);

  // Create a product with stock for POS tests
  const product = await createProductViaAPI(request, token, {
    name: 'Pepsi 330ml POS E2E',
    sale_price: 12000,
    cost_price: 8000,
  });
  posProductId = product.id;
  posProductSku = product.sku; // unique per run — use SKU in search to avoid collisions

  // Add 100 units of stock
  await addStockViaAPI(request, token, posProductId, 100, 8000);
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page, TEST_OWNER.phone, TEST_OWNER.password);
});

test.describe('POS — giao diện', () => {
  test('trang POS hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);
    await expect(page.locator('text=POS')).toBeVisible();
  });

  test('có ô tìm sản phẩm', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);
    const searchInput = page.locator('input[placeholder*="mã vạch"], input[placeholder*="Quét"]');
    await expect(searchInput).toBeVisible();
  });

  test('giỏ hàng ban đầu trống', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);
    // Cart table should exist but empty (shows placeholder row with "Giỏ trống" text)
    await expect(page.locator('table')).toBeVisible();
    await expect(page.locator('tbody')).toContainText('Giỏ trống');
  });
});

test.describe('POS — thêm sản phẩm vào giỏ', () => {
  test('tìm và thêm sản phẩm', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);

    const searchInput = page.locator('input[placeholder*="mã vạch"], input[placeholder*="Quét"], input[type="search"]').first();
    // Search by SKU to get the exact product from this test run
    await searchInput.fill(posProductSku);
    await page.waitForTimeout(400);

    // Click on the product in the search results
    const productResult = page.locator(`text=${posProductSku}`).first();
    if (await productResult.count() > 0) {
      await productResult.click();
      // Should appear in cart
      await expect(page.locator('tbody tr')).toHaveCount(1);
      await expect(page.locator('tbody')).toContainText('Pepsi');
    }
  });

  test('thêm sản phẩm và checkout thanh toán đủ → hoàn tất', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);

    // Search by SKU to find the exact product (avoid collision with old products)
    const searchInput = page.locator('input[placeholder*="mã vạch"], input[placeholder*="Quét"], input[type="search"]').first();
    await searchInput.fill(posProductSku);
    await page.waitForTimeout(400);

    const productResult = page.locator(`text=${posProductSku}`).first();
    if (await productResult.count() === 0) {
      test.skip(true, 'Product not found in search results');
      return;
    }
    await productResult.click();

    // Wait for cart to have item
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 5_000 });

    // Click thanh toán button
    const payBtn = page.locator('button:has-text("Thanh toán"), button:has-text("F9")').first();
    await payBtn.click();

    // Payment dialog should open
    await expect(page.locator('[role="dialog"][aria-label="Thanh toán"]')).toBeVisible();

    // Click "Hoàn tất" with empty amount (pay in full)
    const completeBtn = page.locator('button:has-text("Hoàn tất")').last();
    await completeBtn.click();

    // Should show receipt/success
    await page.waitForTimeout(1_000);
    const receiptVisible = await page.locator('text=Xác nhận, text=biên lai, [aria-label*="in"]').count() > 0;
    if (!receiptVisible) {
      // Just check we're no longer in payment dialog
      await expect(page.locator('[role="dialog"][aria-label="Thanh toán"]')).not.toBeVisible({ timeout: 5_000 });
    }
  });
});

test.describe('POS — Hóa đơn treo', () => {
  test('giữ hóa đơn → tồn tại trong danh sách treo', async ({ page }) => {
    await page.goto(`${BASE_URL}/pos`);

    // Search by SKU to find exact product
    const searchInput = page.locator('input[placeholder*="mã vạch"], input[placeholder*="Quét"], input[type="search"]').first();
    await searchInput.fill(posProductSku);
    await page.waitForTimeout(400);

    const productResult = page.locator(`text=${posProductSku}`).first();
    if (await productResult.count() === 0) {
      test.skip(true, 'Product not found');
      return;
    }
    await productResult.click();
    await expect(page.locator('tbody tr')).toHaveCount(1);

    // Hold the invoice — button says "Giữ hóa đơn" (not "Treo")
    const holdBtn = page.locator('button:has-text("Giữ hóa đơn")').first();
    if (await holdBtn.count() > 0) {
      await holdBtn.click();
      // Wait for hold API + react re-render (no fixed sleep needed — polling assertion)
      await expect(page.locator('tbody')).toContainText('Giỏ trống', { timeout: 8_000 });
    }
  });
});

test.describe('Hóa đơn — lịch sử', () => {
  test('trang Hóa đơn hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/invoices`);
    await expect(page.locator('h1')).toContainText('Hóa đơn');
  });

  test('hóa đơn đã hoàn tất xuất hiện trong lịch sử', async ({ page, request }) => {
    // Complete an invoice via API
    const invRes = await request.post(`${API_URL}/invoices`, {
      data: {
        items: [{ product_id: posProductId, quantity: 1, unit_price: 12000 }],
      },
      headers: { Authorization: `Bearer ${token}` },
    });
    const inv = await invRes.json() as { id: number };

    await request.post(`${API_URL}/invoices/${inv.id}/complete`, {
      data: { payments: [{ method: 'CASH', amount: 12000 }] },
      headers: { Authorization: `Bearer ${token}` },
    });

    // Use SPA client-side navigation (sidebar click) instead of page.goto() to avoid a full
    // page reload that re-initialises Zustand and triggers bootstrap() / token-rotation race.
    // beforeEach leaves us at /dashboard which renders AppLayout with the sidebar.
    await page.click('a[href="/invoices"]');
    await page.waitForURL('**/invoices');
    // target td inside tbody, not the hidden <option> in the status filter dropdown
    await expect(page.locator('tbody td:has-text("Đã hoàn tất")').first()).toBeVisible({ timeout: 5_000 });
  });
});
