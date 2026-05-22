import { http, HttpResponse } from 'msw';

interface RegisterBody {
  shop_name: string;
  owner_name: string;
  phone: string;
  email?: string;
  password: string;
}

interface LoginBody {
  phone: string;
  password: string;
  tenant_id?: number;
}

const successUser = {
  id: 1,
  full_name: 'Chủ shop',
  phone: '0900000001',
  email: null,
  role: 'OWNER' as const,
};

const successTenant = { id: 1, name: 'Shop A', slug: 'shop-a' };

const tokens = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'Bearer',
};

export const handlers = [
  http.post('*/auth/refresh', () =>
    HttpResponse.json({ access_token: 'mock-access-token' }),
  ),
  http.post('*/auth/register', async ({ request }) => {
    const body = (await request.json()) as RegisterBody;
    if (body.phone === '0911111111') {
      return HttpResponse.json(
        { error: { code: 'DUPLICATE_PHONE', message: 'Số điện thoại đã tồn tại' } },
        { status: 409 },
      );
    }
    return HttpResponse.json(
      { user: successUser, tenant: successTenant, ...tokens },
      { status: 201 },
    );
  }),
  http.post('*/auth/login', async ({ request }) => {
    const body = (await request.json()) as LoginBody;
    if (body.password === 'locked') {
      return HttpResponse.json(
        { error: { code: 'ACCOUNT_LOCKED', message: 'Bị khóa' } },
        { status: 429 },
      );
    }
    if (body.password === 'wrong') {
      return HttpResponse.json(
        { error: { code: 'INVALID_CREDENTIALS', message: 'Sai' } },
        { status: 401 },
      );
    }
    return HttpResponse.json({ user: successUser, tenant: successTenant, ...tokens });
  }),
  http.post('*/auth/logout', () => HttpResponse.json({ message: 'ok' })),
  http.get('*/auth/me', () =>
    HttpResponse.json({ user: successUser, tenant: successTenant }),
  ),
  http.put('*/auth/change-password', () =>
    HttpResponse.json({ access_token: 'new-access', refresh_token: 'new-refresh' }),
  ),
  http.get('*/staff', () =>
    HttpResponse.json({
      items: [
        {
          id: 2,
          full_name: 'Nhân viên A',
          phone: '0900000002',
          email: null,
          role: 'CASHIER',
          is_active: true,
          last_login_at: null,
          created_at: '2026-05-22T00:00:00Z',
        },
      ],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    }),
  ),
  http.post('*/staff', async ({ request }) => {
    const body = (await request.json()) as { full_name: string; phone: string };
    return HttpResponse.json(
      {
        id: 99,
        full_name: body.full_name,
        phone: body.phone,
        email: null,
        role: 'CASHIER',
        is_active: true,
        last_login_at: null,
        created_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/staff/:id', async ({ request, params }) => {
    const body = (await request.json()) as { full_name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      full_name: body.full_name ?? 'Nhân viên',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: true,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.patch('*/staff/:id/deactivate', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      full_name: 'Nhân viên A',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: false,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    }),
  ),
  http.patch('*/staff/:id/activate', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      full_name: 'Nhân viên A',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: true,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    }),
  ),
];
