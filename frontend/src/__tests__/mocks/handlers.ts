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

  // ---------- PRODUCTS ----------
  http.get('*/products/search', ({ request }) => {
    const url = new URL(request.url);
    const q = url.searchParams.get('q') ?? '';
    return HttpResponse.json({
      items: q
        ? [
            {
              id: 10,
              sku: 'SP000010',
              barcode: '8934567890123',
              name: `Kết quả ${q}`,
              unit: 'cái',
              sale_price: 15000,
              cost_price: 10000,
              image_url: null,
              allow_negative: false,
              status: 'ACTIVE',
            },
          ]
        : [],
    });
  }),
  http.get('*/products/barcode/:code', ({ params }) => {
    const code = String(params.code);
    if (code === '0000000000000') {
      return HttpResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Không tìm thấy mã vạch' } },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      id: 11,
      sku: 'SP000011',
      barcode: code,
      name: 'Sản phẩm quét mã',
      unit: 'cái',
      sale_price: 20000,
      cost_price: 14000,
      image_url: null,
      allow_negative: false,
      status: 'ACTIVE',
    });
  }),
  http.get('*/products', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search');
    const items =
      search === 'EMPTY'
        ? []
        : [
            {
              id: 1,
              sku: 'SP000001',
              barcode: '8934567890124',
              name: 'Mì tôm Hảo Hảo',
              description: null,
              unit: 'gói',
              cost_price: 3500,
              sale_price: 4500,
              min_stock: 10,
              image_url: null,
              status: 'ACTIVE',
              allow_negative: false,
              category_id: 1,
              category_name: 'Mì gói',
              created_at: '2026-05-22T00:00:00Z',
              updated_at: '2026-05-22T00:00:00Z',
            },
          ];
    return HttpResponse.json({
      items,
      pagination: {
        page: 1,
        limit: 20,
        total: items.length,
        total_pages: items.length ? 1 : 0,
      },
    });
  }),
  http.get('*/products/:id', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      sku: 'SP000001',
      barcode: '8934567890124',
      name: 'Mì tôm Hảo Hảo',
      description: 'Gói 75g',
      unit: 'gói',
      cost_price: 3500,
      sale_price: 4500,
      min_stock: 10,
      image_url: null,
      status: 'ACTIVE',
      allow_negative: false,
      category_id: 1,
      category_name: 'Mì gói',
      created_at: '2026-05-22T00:00:00Z',
      updated_at: '2026-05-22T00:00:00Z',
    }),
  ),
  http.post('*/products', async ({ request }) => {
    const body = (await request.json()) as { name: string; sku?: string };
    if (body.sku === 'DUP') {
      return HttpResponse.json(
        { error: { code: 'DUPLICATE_SKU', message: 'Trùng SKU' } },
        { status: 409 },
      );
    }
    return HttpResponse.json(
      {
        id: 99,
        sku: body.sku ?? 'SP000099',
        barcode: null,
        name: body.name,
        description: null,
        unit: 'cái',
        cost_price: 0,
        sale_price: 0,
        min_stock: 0,
        image_url: null,
        status: 'ACTIVE',
        allow_negative: false,
        category_id: null,
        category_name: null,
        created_at: '2026-05-22T00:00:00Z',
        updated_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/products/:id', async ({ request, params }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      sku: 'SP000001',
      barcode: null,
      name: body.name ?? 'Mì tôm',
      description: null,
      unit: 'gói',
      cost_price: 3500,
      sale_price: 4500,
      min_stock: 10,
      image_url: null,
      status: 'ACTIVE',
      allow_negative: false,
      category_id: 1,
      category_name: 'Mì gói',
      created_at: '2026-05-22T00:00:00Z',
      updated_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.delete('*/products/:id', () =>
    HttpResponse.json({ message: 'Đã ngừng bán sản phẩm' }),
  ),

  // ---------- CATEGORIES ----------
  http.get('*/categories', () =>
    HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'Đồ ăn',
          depth: 1,
          sort_order: 0,
          children: [
            { id: 2, name: 'Mì gói', depth: 2, sort_order: 0, children: [] },
          ],
        },
        {
          id: 3,
          name: 'Đồ uống',
          depth: 1,
          sort_order: 1,
          children: [],
        },
      ],
    }),
  ),
  http.post('*/categories', async ({ request }) => {
    const body = (await request.json()) as { name: string; parent_id?: number | null };
    return HttpResponse.json(
      {
        id: 100,
        name: body.name,
        parent_id: body.parent_id ?? null,
        depth: body.parent_id ? 2 : 1,
        sort_order: 0,
        created_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/categories/:id', async ({ request, params }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      name: body.name ?? 'Đã sửa',
      parent_id: null,
      depth: 1,
      sort_order: 0,
      created_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.delete('*/categories/:id', () =>
    HttpResponse.json({ message: 'Đã xóa nhóm hàng' }),
  ),

  // ---------- CUSTOMERS ----------
  http.get('*/customers/phone/:phone', ({ params }) => {
    if (String(params.phone) === '0999999999') {
      return HttpResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Không tìm thấy' } },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      id: 50,
      name: 'Nguyễn Văn A',
      phone: String(params.phone),
      email: null,
      address: null,
      note: null,
      total_spent: 250000,
      total_orders: 3,
      last_order_at: '2026-05-20T10:00:00Z',
      created_at: '2026-04-01T00:00:00Z',
      updated_at: '2026-05-20T10:00:00Z',
    });
  }),
  http.get('*/customers', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search');
    const items =
      search === 'EMPTY'
        ? []
        : [
            {
              id: 1,
              name: 'Nguyễn Văn A',
              phone: '0901234567',
              email: null,
              address: null,
              note: null,
              total_spent: 250000,
              total_orders: 3,
              last_order_at: '2026-05-20T10:00:00Z',
              created_at: '2026-04-01T00:00:00Z',
              updated_at: '2026-05-20T10:00:00Z',
            },
          ];
    return HttpResponse.json({
      items,
      pagination: {
        page: 1,
        limit: 20,
        total: items.length,
        total_pages: items.length ? 1 : 0,
      },
    });
  }),
  http.get('*/customers/:id', ({ params }) =>
    HttpResponse.json({
      customer: {
        id: Number(params.id),
        name: 'Nguyễn Văn A',
        phone: '0901234567',
        email: 'a@example.com',
        address: 'Hà Nội',
        note: null,
        total_spent: 250000,
        total_orders: 3,
        last_order_at: '2026-05-20T10:00:00Z',
        created_at: '2026-04-01T00:00:00Z',
        updated_at: '2026-05-20T10:00:00Z',
      },
      recent_orders: [
        {
          invoice_id: 11,
          code: 'HD20260520-001',
          total: 100000,
          completed_at: '2026-05-20T10:00:00Z',
          status: 'COMPLETED',
        },
      ],
    }),
  ),
  http.post('*/customers', async ({ request }) => {
    const body = (await request.json()) as { name: string; phone?: string };
    return HttpResponse.json(
      {
        id: 200,
        name: body.name,
        phone: body.phone ?? null,
        email: null,
        address: null,
        note: null,
        total_spent: 0,
        total_orders: 0,
        last_order_at: null,
        created_at: '2026-05-22T00:00:00Z',
        updated_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/customers/:id', async ({ request, params }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      name: body.name ?? 'KH',
      phone: '0901234567',
      email: null,
      address: null,
      note: null,
      total_spent: 0,
      total_orders: 0,
      last_order_at: null,
      created_at: '2026-05-22T00:00:00Z',
      updated_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.delete('*/customers/:id', () =>
    HttpResponse.json({ message: 'Đã xóa khách hàng' }),
  ),

  // ---------- SUPPLIERS ----------
  http.get('*/suppliers', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search');
    const items =
      search === 'EMPTY'
        ? []
        : [
            {
              id: 1,
              name: 'NCC Acecook',
              phone: '0901111111',
              email: null,
              address: null,
              tax_code: '0102030405',
              note: null,
              total_debt: 1500000,
              created_at: '2026-04-01T00:00:00Z',
              updated_at: '2026-05-20T10:00:00Z',
            },
          ];
    return HttpResponse.json({
      items,
      pagination: {
        page: 1,
        limit: 20,
        total: items.length,
        total_pages: items.length ? 1 : 0,
      },
    });
  }),
  http.get('*/suppliers/:id', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      name: 'NCC Acecook',
      phone: '0901111111',
      email: null,
      address: null,
      tax_code: '0102030405',
      note: null,
      total_debt: 1500000,
      created_at: '2026-04-01T00:00:00Z',
      updated_at: '2026-05-20T10:00:00Z',
    }),
  ),
  http.post('*/suppliers', async ({ request }) => {
    const body = (await request.json()) as { name: string };
    return HttpResponse.json(
      {
        id: 300,
        name: body.name,
        phone: null,
        email: null,
        address: null,
        tax_code: null,
        note: null,
        total_debt: 0,
        created_at: '2026-05-22T00:00:00Z',
        updated_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/suppliers/:id', async ({ request, params }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      name: body.name ?? 'NCC',
      phone: null,
      email: null,
      address: null,
      tax_code: null,
      note: null,
      total_debt: 0,
      created_at: '2026-05-22T00:00:00Z',
      updated_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.delete('*/suppliers/:id', () =>
    HttpResponse.json({ message: 'Đã xóa nhà cung cấp' }),
  ),
];
