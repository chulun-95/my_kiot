import { type Page, type APIRequestContext } from '@playwright/test';

export const BASE_URL = 'http://localhost:5173';
export const API_URL = 'http://127.0.0.1:8000/api/v1';

/** Navigate to login and authenticate via UI */
export async function loginViaUI(
  page: Page,
  phone: string,
  password: string,
) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('h1:has-text("Đăng nhập")');
  await page.locator('input[type="tel"]').fill(phone);
  await page.locator('#login-password').fill(password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard', { timeout: 15_000 });
}

/** Register a new shop via API — returns { access_token } */
export async function registerViaAPI(
  request: APIRequestContext,
  opts: { phone: string; password: string; shop_name?: string; owner_name?: string },
) {
  const res = await request.post(`${API_URL}/auth/register`, {
    data: {
      shop_name: opts.shop_name ?? `Shop ${opts.phone}`,
      owner_name: opts.owner_name ?? 'Owner Test',
      phone: opts.phone,
      password: opts.password,
    },
  });
  return await res.json() as { access_token: string };
}

/** Login via API — returns access_token */
export async function loginViaAPI(
  request: APIRequestContext,
  phone: string,
  password: string,
) {
  const res = await request.post(`${API_URL}/auth/login`, {
    data: { phone, password },
  });
  const body = await res.json() as { access_token: string };
  return body.access_token;
}

/** Create a product via API */
export async function createProductViaAPI(
  request: APIRequestContext,
  token: string,
  product: { name: string; sale_price: number; cost_price?: number; allow_negative?: boolean },
) {
  const res = await request.post(`${API_URL}/products`, {
    data: {
      name: product.name,
      sale_price: product.sale_price,
      cost_price: product.cost_price ?? 0,
      allow_negative: product.allow_negative ?? false,
    },
    headers: { Authorization: `Bearer ${token}` },
  });
  return await res.json() as { id: number; name: string; sku: string };
}

/** Create and complete a goods receipt to add stock */
export async function addStockViaAPI(
  request: APIRequestContext,
  token: string,
  productId: number,
  qty: number,
  costPrice = 10000,
) {
  // Create draft receipt — pay in full to avoid DEBT_REQUIRES_SUPPLIER validation
  const paidAmount = qty * costPrice;
  const draftRes = await request.post(`${API_URL}/goods-receipts`, {
    data: {
      items: [{ product_id: productId, quantity: qty, cost_price: costPrice }],
      paid_amount: paidAmount,
    },
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!draftRes.ok()) {
    const body = await draftRes.text();
    throw new Error(`addStockViaAPI: create receipt failed ${draftRes.status()}: ${body}`);
  }
  const draft = await draftRes.json() as { id: number };

  // Complete it
  const completeRes = await request.post(`${API_URL}/goods-receipts/${draft.id}/complete`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!completeRes.ok()) {
    const body = await completeRes.text();
    throw new Error(`addStockViaAPI: complete receipt failed ${completeRes.status()}: ${body}`);
  }
  return draft.id;
}
