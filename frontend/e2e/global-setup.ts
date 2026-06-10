import { chromium, type FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const _dirname = typeof __dirname !== 'undefined'
  ? __dirname
  : path.dirname(fileURLToPath(import.meta.url));

const AUTH_FILE = path.join(_dirname, '.auth', 'owner.json');
const BASE_URL = 'http://localhost:5173';

export const TEST_OWNER = {
  phone: '0901000001',
  password: 'secret123',
  shop_name: 'Tạp Hóa E2E',
  owner_name: 'Chủ Shop Test',
};

export default async function globalSetup(_config: FullConfig) {
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Try registration first; if user already exists, fall back to login
  await page.goto(`${BASE_URL}/register`);
  await page.waitForSelector('h1:has-text("Đăng ký shop mới")');

  await page.getByText('Tên shop').locator('..').locator('input').fill(TEST_OWNER.shop_name);
  await page.getByText('Tên chủ shop').locator('..').locator('input').fill(TEST_OWNER.owner_name);
  await page.locator('input[type="tel"]').fill(TEST_OWNER.phone);
  await page.locator('input[type="password"]').fill(TEST_OWNER.password);
  await page.click('button[type="submit"]');

  // Wait for either successful redirect or an error message (user already registered)
  const result = await Promise.race([
    page.waitForURL('**/dashboard', { timeout: 10_000 }).then(() => 'dashboard'),
    page.waitForSelector('[role="alert"], .text-rose-600, [class*="error"]', { timeout: 10_000 }).then(() => 'error'),
  ]).catch(() => 'timeout');

  if (result !== 'dashboard') {
    // Registration failed (likely phone already registered) — fall back to login
    await page.goto(`${BASE_URL}/login`);
    await page.waitForSelector('h1:has-text("Đăng nhập")');
    await page.locator('input[type="tel"]').fill(TEST_OWNER.phone);
    await page.locator('#login-password').fill(TEST_OWNER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 15_000 });
  }

  // Save authenticated state (cookies)
  await context.storageState({ path: AUTH_FILE });
  await browser.close();
}
