import { test, expect } from '@playwright/test';
import { BASE_URL, loginViaUI } from './helpers';

// Auth spec uses unique phone numbers per run to avoid conflicts on reused DB
function uniquePhone(seed = 0): string {
  // Format: 09 + 8 digits (valid Vietnamese mobile)
  const suffix = ((Date.now() + seed) % 100_000_000).toString().padStart(8, '0');
  return `09${suffix}`;
}

test.describe('Đăng ký shop', () => {
  test('đăng ký thành công → chuyển về /dashboard', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await page.waitForSelector('h1:has-text("Đăng ký shop mới")');

    await page.getByText('Tên shop').locator('..').locator('input').fill('Tạp Hóa Auth Test');
    await page.getByText('Tên chủ shop').locator('..').locator('input').fill('Chủ Shop');
    await page.locator('input[type="tel"]').fill(uniquePhone(1));
    await page.locator('input[type="password"]').fill('secret123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('SĐT trùng → hiện lỗi', async ({ page }) => {
    const dupPhone = uniquePhone(2);
    // Register first
    await page.goto(`${BASE_URL}/register`);
    await page.getByText('Tên shop').locator('..').locator('input').fill('Shop Dupe');
    await page.getByText('Tên chủ shop').locator('..').locator('input').fill('Owner');
    await page.locator('input[type="tel"]').fill(dupPhone);
    await page.locator('input[type="password"]').fill('secret123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');

    // Logout
    await page.click('button:has-text("Đăng xuất")');
    await page.waitForURL('**/login');

    // Register again with same phone
    await page.goto(`${BASE_URL}/register`);
    await page.getByText('Tên shop').locator('..').locator('input').fill('Shop Dupe 2');
    await page.getByText('Tên chủ shop').locator('..').locator('input').fill('Owner 2');
    await page.locator('input[type="tel"]').fill(dupPhone);
    await page.locator('input[type="password"]').fill('secret123');
    await page.click('button[type="submit"]');

    await expect(page.locator('[role="alert"]')).toBeVisible();
  });
});

test.describe('Đăng nhập', () => {
  test('đăng nhập thành công → /dashboard', async ({ page }) => {
    await loginViaUI(page, '0901000001', 'secret123');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('sai mật khẩu → hiện thông báo lỗi', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="tel"]').fill('0901000001');
    await page.locator('#login-password').fill('wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('[role="alert"]')).toBeVisible();
    await expect(page).toHaveURL(/login/);
  });

  test('SĐT không tồn tại → hiện thông báo lỗi', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="tel"]').fill('0909999999');
    await page.locator('#login-password').fill('secret123');
    await page.click('button[type="submit"]');

    await expect(page.locator('[role="alert"]')).toBeVisible();
  });
});

test.describe('Đăng xuất', () => {
  test('nhấn Đăng xuất → redirect về /login', async ({ page }) => {
    await loginViaUI(page, '0901000001', 'secret123');
    await page.click('button:has-text("Đăng xuất")');
    await page.waitForURL('**/login');
    await expect(page).toHaveURL(/login/);
  });

  test('sau khi logout, truy cập /dashboard → redirect về /login', async ({ page }) => {
    await loginViaUI(page, '0901000001', 'secret123');
    await page.click('button:has-text("Đăng xuất")');
    await page.waitForURL('**/login');

    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForURL('**/login');
    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Đổi mật khẩu', () => {
  test('đổi mật khẩu thành công → hiện thông báo thành công', async ({ page }) => {
    // Use dedicated account with unique phone to avoid conflicts
    const changePwPhone = uniquePhone(3);
    await page.goto(`${BASE_URL}/register`);
    await page.getByText('Tên shop').locator('..').locator('input').fill('Shop Changepw');
    await page.getByText('Tên chủ shop').locator('..').locator('input').fill('Owner Changepw');
    await page.locator('input[type="tel"]').fill(changePwPhone);
    await page.locator('input[type="password"]').fill('oldpass1');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');

    await page.goto(`${BASE_URL}/me/change-password`);
    await page.waitForSelector('h1');

    const inputs = page.locator('input[type="password"]');
    await inputs.nth(0).fill('oldpass1');
    await inputs.nth(1).fill('newpass1');
    await inputs.nth(2).fill('newpass1');
    await page.click('button[type="submit"]');

    // Should show success message or redirect
    await expect(
      page.locator('text=/thành công|đổi mật khẩu/i').first()
    ).toBeVisible({ timeout: 8_000 });
  });
});
