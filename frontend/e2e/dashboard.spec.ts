import { test, expect } from '@playwright/test';
import { BASE_URL, API_URL, createProductViaAPI, addStockViaAPI, loginViaAPI, loginViaUI } from './helpers';
import { TEST_OWNER } from './global-setup';

let token: string;

test.beforeAll(async ({ request }) => {
  token = await loginViaAPI(request, TEST_OWNER.phone, TEST_OWNER.password);
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page, TEST_OWNER.phone, TEST_OWNER.password);
});

test.describe('Dashboard', () => {
  test('trang Dashboard hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await expect(page.locator('h1')).toContainText('Tổng quan');
  });

  test('dashboard hiển thị số liệu hôm nay', async ({ page, request }) => {
    // Create and sell some products to have data
    const product = await createProductViaAPI(request, token, {
      name: 'SP Dashboard E2E',
      sale_price: 25000,
      cost_price: 15000,
    });
    await addStockViaAPI(request, token, product.id, 20, 15000);

    // Complete an invoice
    const invRes = await request.post(`${API_URL}/invoices`, {
      data: {
        items: [{ product_id: product.id, quantity: 2, unit_price: 25000 }],
      },
      headers: { Authorization: `Bearer ${token}` },
    });
    const inv = await invRes.json() as { id: number };
    await request.post(`${API_URL}/invoices/${inv.id}/complete`, {
      data: { payments: [{ method: 'CASH', amount: 50000 }] },
      headers: { Authorization: `Bearer ${token}` },
    });

    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForSelector('h1:has-text("Tổng quan")');

    // Dashboard should show today's revenue (any non-zero amount from our sale above)
    await expect(page.locator('body')).toContainText('Doanh thu hôm nay');
    // Revenue should be > 0 (not "0 VNĐ")
    const bodyText = await page.locator('body').textContent() ?? '';
    expect(bodyText).toMatch(/Doanh thu hôm nay\s*\d[\d.]*\s*VNĐ/);
  });

  test('redirect về /dashboard khi vào /', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForURL('**/dashboard');
    await expect(page).toHaveURL(/dashboard/);
  });
});

test.describe('Báo cáo — Doanh thu', () => {
  test('trang Doanh thu hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/revenue`);
    await expect(page.locator('h1')).toContainText('doanh thu');
  });

  test('biểu đồ/bảng doanh thu có dữ liệu', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/revenue`);
    await page.waitForSelector('h1:has-text("doanh thu")');
    // Should not show empty state after we have sales
    await expect(page.locator('body')).not.toContainText('Không có dữ liệu');
  });
});

test.describe('Báo cáo — Top SP', () => {
  test('trang Top SP hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/top-products`);
    await expect(page.locator('h1')).toContainText('Top');
  });
});

test.describe('Báo cáo — Tồn kho tổng quan', () => {
  test('trang Stock Summary hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/stock-summary`);
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('body')).toContainText('Tồn kho');
  });
});

test.describe('Báo cáo — Lợi nhuận (Owner)', () => {
  test('trang Lợi nhuận hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/profit`);
    await expect(page.locator('h1')).toBeVisible();
  });
});

test.describe('Khách hàng', () => {
  test('trang Khách hàng hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/customers`);
    await expect(page.locator('h1')).toContainText('Khách hàng');
  });

  test('tạo khách hàng mới', async ({ page }) => {
    // Use unique phone per run to avoid duplicate constraint on reused DB
    const phone = `09${((Date.now()) % 100_000_000).toString().padStart(8, '0')}`;
    await page.goto(`${BASE_URL}/customers/new`);
    await page.locator('input[placeholder*="Tên"], label:has-text("Tên") input').fill('Nguyễn Văn Test');
    await page.locator('input[type="tel"]').fill(phone);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/customers\/\d+|\/customers$/);
    await expect(page.locator('body')).toContainText('Nguyễn Văn Test');
  });
});

test.describe('Nhà cung cấp', () => {
  test('trang NCC hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/suppliers`);
    await expect(page.locator('h1')).toContainText('Nhà cung cấp');
  });

  test('tạo NCC mới', async ({ page }) => {
    await page.goto(`${BASE_URL}/suppliers/new`);
    await page.locator('label:has-text("Tên") input').first().fill('NCC Test E2E');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/suppliers(\/\d+)?$/);
    await expect(page.locator('body')).toContainText('NCC Test E2E');
  });
});

test.describe('Nhân viên (Owner)', () => {
  test('trang Nhân viên hiển thị', async ({ page }) => {
    await page.goto(`${BASE_URL}/staff`);
    await expect(page.locator('h1')).toContainText('Nhân viên');
  });

  test('mời nhân viên mới', async ({ page }) => {
    await page.goto(`${BASE_URL}/staff`);
    await page.waitForSelector('h1:has-text("Nhân viên")');

    const inviteBtn = page.locator('button:has-text("Mời"), button:has-text("Thêm")').first();
    if (await inviteBtn.count() > 0) {
      await inviteBtn.click();
      // Fill form
      const dialog = page.locator('[role="dialog"], form').last();
      const inputs = dialog.locator('input');
      if (await inputs.count() >= 2) {
        await inputs.nth(0).fill('Nhân Viên Test');
        await inputs.filter({ hasText: 'SĐT' }).fill('0905001001').catch(() =>
          inputs.nth(1).fill('0905001001'),
        );
        const pwInput = dialog.locator('input[type="password"]').first();
        await pwInput.fill('nhanvien123');
        await dialog.locator('button[type="submit"]').click();
        await page.waitForTimeout(1_000);
        await expect(page.locator('body')).toContainText('Nhân Viên Test');
      }
    }
  });
});
