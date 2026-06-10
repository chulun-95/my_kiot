import { test, expect } from '@playwright/test';
import { BASE_URL, loginViaUI } from './helpers';
import { TEST_OWNER } from './global-setup';

test.beforeEach(async ({ page }) => {
  await loginViaUI(page, TEST_OWNER.phone, TEST_OWNER.password);
});

test.describe('Sản phẩm — danh sách', () => {
  test('hiển thị trang Sản phẩm', async ({ page }) => {
    await page.goto(`${BASE_URL}/products`);
    await expect(page.locator('h1')).toContainText('Sản phẩm');
  });

  test('nút Thêm sản phẩm tồn tại', async ({ page }) => {
    await page.goto(`${BASE_URL}/products`);
    await expect(page.locator('a:has-text("Thêm")')).toBeVisible();
  });
});

test.describe('Sản phẩm — tạo mới', () => {
  test('tạo sản phẩm tối thiểu → xuất hiện trong danh sách', async ({ page }) => {
    await page.goto(`${BASE_URL}/products/new`);
    await expect(page.locator('h1')).toContainText('Thêm sản phẩm');

    await page.locator('input').first().fill('Coca-Cola Test E2E');

    // Sale price (MoneyInput)
    const salePriceInput = page.locator('label:has-text("Giá bán")').locator('input');
    await salePriceInput.fill('15000');

    await page.click('button[type="submit"]');

    // Should redirect to product detail
    await page.waitForURL(/\/products\/\d+/, { timeout: 10_000 });
    await expect(page.locator('body')).toContainText('Coca-Cola Test E2E');
  });

  test('tạo sản phẩm với đầy đủ thông tin', async ({ page }) => {
    // Use unique SKU/barcode per run to avoid partial-unique-index conflicts on reused DB
    const suffix = (Date.now() % 100_000).toString().padStart(5, '0');
    const sku = `MIHAOHAO${suffix}`;
    const barcode = `89345631${suffix}`; // 8 + 5 = 13 digits (EAN-13)

    await page.goto(`${BASE_URL}/products/new`);

    // Name
    await page.locator('input').first().fill('Mì Tôm Hảo Hảo E2E');

    // SKU
    const skuInput = page.locator('label:has-text("SKU")').locator('input');
    await skuInput.fill(sku);

    // Barcode
    const barcodeInput = page.locator('label:has-text("Mã vạch")').locator('input');
    await barcodeInput.fill(barcode);

    // Sale price
    const salePriceInput = page.locator('label:has-text("Giá bán")').locator('input');
    await salePriceInput.fill('4500');

    // Cost price (Owner sees it)
    const costPriceInput = page.locator('label:has-text("Giá vốn")').locator('input');
    if (await costPriceInput.count() > 0) {
      await costPriceInput.fill('3000');
    }

    await page.click('button[type="submit"]');
    await page.waitForURL(/\/products\/\d+/);
    await expect(page.locator('body')).toContainText('Mì Tôm Hảo Hảo E2E');
    await expect(page.locator('body')).toContainText(sku);
  });

  test('tên rỗng → form không submit', async ({ page }) => {
    await page.goto(`${BASE_URL}/products/new`);
    await page.click('button[type="submit"]');
    // Should still be on the form page
    await expect(page).toHaveURL(/products\/new/);
  });
});

test.describe('Sản phẩm — tìm kiếm', () => {
  test('tìm kiếm theo tên → hiện kết quả', async ({ page }) => {
    await page.goto(`${BASE_URL}/products`);
    await page.waitForSelector('h1:has-text("Sản phẩm")');

    const searchInput = page.locator('input[placeholder*="Tìm"], input[type="search"], input[placeholder*="tìm"]').first();
    if (await searchInput.count() > 0) {
      await searchInput.fill('Coca');
      await page.waitForTimeout(500); // debounce
      await expect(page.locator('body')).toContainText('Coca');
    }
  });
});

test.describe('Sản phẩm — sửa', () => {
  test('sửa tên sản phẩm → hiện tên mới', async ({ page }) => {
    // Create a product first
    await page.goto(`${BASE_URL}/products/new`);
    await page.locator('input').first().fill('SP Cần Sửa E2E');
    await page.locator('label:has-text("Giá bán")').locator('input').fill('5000');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/products\/\d+/);

    // Go to edit
    const editLink = page.locator('a:has-text("Sửa")').first();
    if (await editLink.count() > 0) {
      await editLink.click();
      await page.waitForURL(/\/products\/\d+\/edit/);

      // Change name
      const nameInput = page.locator('input').first();
      await nameInput.fill('SP Đã Sửa E2E');
      await page.click('button[type="submit"]');
      await page.waitForURL(/\/products\/\d+/);
      await expect(page.locator('body')).toContainText('SP Đã Sửa E2E');
    }
  });
});

test.describe('Nhóm hàng', () => {
  test('trang Nhóm hàng hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/categories`);
    await expect(page.locator('h1')).toContainText('Nhóm hàng');
  });

  test('tạo nhóm hàng mới', async ({ page }) => {
    await page.goto(`${BASE_URL}/categories`);
    await page.waitForSelector('h1:has-text("Nhóm hàng")');

    const addBtn = page.locator('button:has-text("Thêm"), a:has-text("Thêm nhóm")').first();
    if (await addBtn.count() > 0) {
      await addBtn.click();
      // Fill in category name if dialog opens
      const dialog = page.locator('[role="dialog"], form').last();
      const nameInput = dialog.locator('input').first();
      await nameInput.fill('Đồ Uống E2E');
      const submitBtn = dialog.locator('button[type="submit"]').first();
      await submitBtn.click();
      await expect(page.locator('body')).toContainText('Đồ Uống E2E');
    }
  });
});
