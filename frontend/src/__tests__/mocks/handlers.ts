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
    HttpResponse.json({
      user: { id: 1, full_name: 'Owner A', role: 'OWNER' },
      tenant: { id: 1, name: 'Shop A', slug: 'shop-a' },
      access_token: 'access-1',
    }),
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

  // ---------- DEBT REPORTS (before generic /customers to match first) ----------
  http.get('*/reports/debts/customers', () =>
    HttpResponse.json({
      items: [{ partner_id: 1, partner_name: 'Nguyễn Văn A', phone: '0905111222', debt: 14000 }],
      total_debt: 14000,
    }),
  ),
  http.get('*/reports/debts/suppliers', () =>
    HttpResponse.json({
      items: [{ partner_id: 2, partner_name: 'NCC X', phone: null, debt: 150000 }],
      total_debt: 150000,
    }),
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

  // ---------- GOODS RECEIPTS ----------
  http.get('*/goods-receipts', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const items =
      status === 'EMPTY'
        ? []
        : [
            {
              id: 1,
              code: 'NK20260520-001',
              supplier_id: 1,
              supplier_name: 'NCC Acecook',
              total: 350000,
              paid_amount: 350000,
              status: 'COMPLETED',
              completed_at: '2026-05-20T10:00:00Z',
              created_at: '2026-05-20T09:00:00Z',
            },
            {
              id: 2,
              code: 'NK20260521-001',
              supplier_id: null,
              supplier_name: null,
              total: 0,
              paid_amount: 0,
              status: 'DRAFT',
              completed_at: null,
              created_at: '2026-05-21T08:30:00Z',
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
  http.get('*/goods-receipts/:id', ({ params }) => {
    const id = Number(params.id);
    const isDraft = id === 2;
    return HttpResponse.json({
      id,
      code: isDraft ? 'NK20260521-001' : 'NK20260520-001',
      supplier_id: isDraft ? null : 1,
      supplier_name: isDraft ? null : 'NCC Acecook',
      total: isDraft ? 0 : 350000,
      paid_amount: isDraft ? 0 : 350000,
      status: isDraft ? 'DRAFT' : 'COMPLETED',
      note: null,
      completed_at: isDraft ? null : '2026-05-20T10:00:00Z',
      created_at: isDraft ? '2026-05-21T08:30:00Z' : '2026-05-20T09:00:00Z',
      items: isDraft
        ? []
        : [
            {
              id: 10,
              product_id: 1,
              product_name: 'Mì tôm Hảo Hảo',
              product_sku: 'SP000001',
              quantity: 100,
              cost_price: 3500,
              line_total: 350000,
            },
          ],
    });
  }),
  http.post('*/goods-receipts', async ({ request }) => {
    const body = (await request.json()) as {
      supplier_id?: number | null;
      items: Array<{ product_id: number; quantity: number; cost_price: number }>;
      paid_amount?: number;
      note?: string;
    };
    const total = body.items.reduce(
      (s, it) => s + it.quantity * it.cost_price,
      0,
    );
    return HttpResponse.json(
      {
        id: 99,
        code: 'NK20260523-001',
        supplier_id: body.supplier_id ?? null,
        supplier_name: body.supplier_id ? 'NCC' : null,
        total,
        paid_amount: body.paid_amount ?? 0,
        status: 'DRAFT',
        note: body.note ?? null,
        completed_at: null,
        created_at: '2026-05-23T08:00:00Z',
        items: body.items.map((it, idx) => ({
          id: idx + 1,
          product_id: it.product_id,
          product_name: `SP ${it.product_id}`,
          product_sku: `SP${String(it.product_id).padStart(6, '0')}`,
          quantity: it.quantity,
          cost_price: it.cost_price,
          line_total: it.quantity * it.cost_price,
        })),
      },
      { status: 201 },
    );
  }),
  http.put('*/goods-receipts/:id', async ({ request, params }) => {
    const body = (await request.json()) as {
      items?: Array<{ product_id: number; quantity: number; cost_price: number }>;
      paid_amount?: number;
      note?: string;
    };
    const items = body.items ?? [];
    const total = items.reduce((s, it) => s + it.quantity * it.cost_price, 0);
    return HttpResponse.json({
      id: Number(params.id),
      code: 'NK20260521-001',
      supplier_id: null,
      supplier_name: null,
      total,
      paid_amount: body.paid_amount ?? 0,
      status: 'DRAFT',
      note: body.note ?? null,
      completed_at: null,
      created_at: '2026-05-21T08:30:00Z',
      items: items.map((it, idx) => ({
        id: idx + 1,
        product_id: it.product_id,
        product_name: `SP ${it.product_id}`,
        product_sku: `SP${String(it.product_id).padStart(6, '0')}`,
        quantity: it.quantity,
        cost_price: it.cost_price,
        line_total: it.quantity * it.cost_price,
      })),
    });
  }),
  http.post('*/goods-receipts/:id/complete', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      code: 'NK20260521-001',
      supplier_id: null,
      supplier_name: null,
      total: 0,
      paid_amount: 0,
      status: 'COMPLETED',
      note: null,
      completed_at: '2026-05-23T08:30:00Z',
      created_at: '2026-05-21T08:30:00Z',
      items: [],
    }),
  ),
  http.post('*/goods-receipts/:id/cancel', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      code: 'NK20260521-001',
      supplier_id: null,
      supplier_name: null,
      total: 0,
      paid_amount: 0,
      status: 'CANCELLED',
      note: null,
      completed_at: null,
      created_at: '2026-05-21T08:30:00Z',
      items: [],
    }),
  ),

  // ---------- INVENTORY ----------
  http.get('*/inventory/low-stock', () =>
    HttpResponse.json({
      items: [
        {
          product_id: 2,
          product_sku: 'SP000002',
          product_name: 'Coca 330ml',
          unit: 'lon',
          quantity: 0,
          min_stock: 12,
          severity: 'OUT_OF_STOCK',
          shortage: 12,
        },
        {
          product_id: 1,
          product_sku: 'SP000001',
          product_name: 'Mì tôm Hảo Hảo',
          unit: 'gói',
          quantity: 3,
          min_stock: 10,
          severity: 'LOW',
          shortage: 7,
        },
      ],
      summary: {
        out_of_stock_count: 1,
        low_count: 1,
        total_count: 2,
      },
    }),
  ),
  http.get('*/inventory/adjustments', () =>
    HttpResponse.json({
      items: [
        {
          id: 5,
          product_id: 1,
          product_name: 'Mì tôm Hảo Hảo',
          product_sku: 'SP000001',
          quantity: -2,
          balance_after: 8,
          note: 'Kiểm kê tháng',
          created_at: '2026-05-22T10:00:00Z',
          created_by: 1,
        },
      ],
      pagination: { page: 1, limit: 50, total: 1, total_pages: 1 },
    }),
  ),
  http.post('*/inventory/adjustments', async ({ request }) => {
    const body = (await request.json()) as {
      items: Array<{ product_id: number; new_quantity: number; reason?: string }>;
    };
    return HttpResponse.json(
      {
        items: body.items.map((it, idx) => ({
          product_id: it.product_id,
          product_name: `SP ${it.product_id}`,
          product_sku: `SP${String(it.product_id).padStart(6, '0')}`,
          old_quantity: 10,
          new_quantity: it.new_quantity,
          delta: it.new_quantity - 10,
          movement_id: 100 + idx,
        })),
      },
      { status: 201 },
    );
  }),
  http.get('*/inventory/:productId/movements', ({ params }) =>
    HttpResponse.json({
      items: [
        {
          id: 1,
          quantity: 100,
          unit_cost: 3500,
          type: 'RECEIPT',
          ref_type: 'GOODS_RECEIPT',
          ref_id: 1,
          balance_after: 100,
          note: null,
          created_at: '2026-05-20T10:00:00Z',
        },
        {
          id: 2,
          quantity: -2,
          unit_cost: 3500,
          type: 'SALE',
          ref_type: 'INVOICE',
          ref_id: 5,
          balance_after: 98,
          note: null,
          created_at: '2026-05-21T11:00:00Z',
        },
      ],
      pagination: { page: 1, limit: 50, total: 2, total_pages: 1 },
      product_id: Number(params.productId),
    }),
  ),
  // ---------- INVOICES ----------
  http.get('*/invoices/drafts', () =>
    HttpResponse.json({
      items: [
        {
          id: 70,
          code: 'HD20260523-001',
          customer_id: null,
          customer_name: null,
          cashier_id: 1,
          total: 50000,
          paid_amount: 0,
          status: 'DRAFT',
          completed_at: null,
          created_at: '2026-05-23T08:00:00Z',
        },
      ],
    }),
  ),
  http.get('*/invoices/:id', ({ params }) => {
    const id = Number(params.id);
    if (id === 0) {
      return HttpResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Không tìm thấy' } },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      id,
      code: 'HD20260523-001',
      customer_id: 1,
      customer_name: 'Nguyễn Văn A',
      cashier_id: 1,
      cashier_name: 'Chủ shop',
      subtotal: 100000,
      discount_amount: 0,
      total: 100000,
      cost_total: 70000,
      paid_amount: 100000,
      change_amount: 0,
      status: 'COMPLETED',
      note: null,
      completed_at: '2026-05-23T09:00:00Z',
      cancelled_at: null,
      cancel_reason: null,
      created_at: '2026-05-23T08:55:00Z',
      items: [
        {
          id: 1,
          product_id: 1,
          product_name: 'Mì tôm Hảo Hảo',
          product_sku: 'SP000001',
          unit: 'gói',
          quantity: 10,
          unit_price: 10000,
          cost_price: 7000,
          discount_amount: 0,
          line_total: 100000,
        },
      ],
      payments: [
        {
          id: 1,
          method: 'CASH',
          amount: 100000,
          note: null,
          created_at: '2026-05-23T09:00:00Z',
        },
      ],
    });
  }),
  http.get('*/invoices', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const items =
      status === 'EMPTY'
        ? []
        : [
            {
              id: 11,
              code: 'HD20260523-001',
              customer_id: 1,
              customer_name: 'Nguyễn Văn A',
              cashier_id: 1,
              total: 100000,
              paid_amount: 100000,
              status: 'COMPLETED',
              completed_at: '2026-05-23T09:00:00Z',
              created_at: '2026-05-23T08:55:00Z',
            },
            {
              id: 12,
              code: 'HD20260523-002',
              customer_id: null,
              customer_name: null,
              cashier_id: 1,
              total: 50000,
              paid_amount: 0,
              status: 'DRAFT',
              completed_at: null,
              created_at: '2026-05-23T10:00:00Z',
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
  http.post('*/invoices', async ({ request }) => {
    const body = (await request.json()) as {
      customer_id?: number | null;
      items?: Array<{
        product_id: number;
        quantity: number;
        unit_price?: number;
        discount_amount?: number;
      }>;
      discount_amount?: number;
      note?: string | null;
    };
    const items = body.items ?? [];
    const subtotal = items.reduce(
      (s, it) => s + (it.unit_price ?? 10000) * it.quantity,
      0,
    );
    return HttpResponse.json(
      {
        id: 200,
        code: 'HD20260523-NEW',
        customer_id: body.customer_id ?? null,
        customer_name: body.customer_id ? 'KH' : null,
        cashier_id: 1,
        cashier_name: 'Chủ shop',
        subtotal,
        discount_amount: body.discount_amount ?? 0,
        total: subtotal - (body.discount_amount ?? 0),
        cost_total: 0,
        paid_amount: 0,
        change_amount: 0,
        status: 'DRAFT',
        note: body.note ?? null,
        completed_at: null,
        cancelled_at: null,
        cancel_reason: null,
        created_at: '2026-05-23T08:00:00Z',
        items: items.map((it, idx) => ({
          id: idx + 1,
          product_id: it.product_id,
          product_name: `SP ${it.product_id}`,
          product_sku: `SP${String(it.product_id).padStart(6, '0')}`,
          unit: 'cái',
          quantity: it.quantity,
          unit_price: it.unit_price ?? 10000,
          cost_price: 0,
          discount_amount: it.discount_amount ?? 0,
          line_total: (it.unit_price ?? 10000) * it.quantity,
        })),
        payments: [],
      },
      { status: 201 },
    );
  }),
  http.put('*/invoices/:id', async ({ request, params }) => {
    const body = (await request.json()) as {
      customer_id?: number | null;
      items?: Array<{
        product_id: number;
        quantity: number;
        unit_price?: number;
        discount_amount?: number;
      }>;
      discount_amount?: number | null;
      note?: string | null;
    };
    const items = body.items ?? [];
    const subtotal = items.reduce(
      (s, it) => s + (it.unit_price ?? 10000) * it.quantity,
      0,
    );
    return HttpResponse.json({
      id: Number(params.id),
      code: 'HD20260523-001',
      customer_id: body.customer_id ?? null,
      customer_name: null,
      cashier_id: 1,
      cashier_name: 'Chủ shop',
      subtotal,
      discount_amount: body.discount_amount ?? 0,
      total: subtotal - (Number(body.discount_amount) || 0),
      cost_total: 0,
      paid_amount: 0,
      change_amount: 0,
      status: 'DRAFT',
      note: body.note ?? null,
      completed_at: null,
      cancelled_at: null,
      cancel_reason: null,
      created_at: '2026-05-23T08:00:00Z',
      items: items.map((it, idx) => ({
        id: idx + 1,
        product_id: it.product_id,
        product_name: `SP ${it.product_id}`,
        product_sku: `SP${String(it.product_id).padStart(6, '0')}`,
        unit: 'cái',
        quantity: it.quantity,
        unit_price: it.unit_price ?? 10000,
        cost_price: 0,
        discount_amount: it.discount_amount ?? 0,
        line_total: (it.unit_price ?? 10000) * it.quantity,
      })),
      payments: [],
    });
  }),
  http.post('*/invoices/:id/complete', async ({ request, params }) => {
    const body = (await request.json()) as {
      payments: Array<{ method: string; amount: number }>;
      allow_debt?: boolean;
    };
    if (Number(params.id) === 9999) {
      return HttpResponse.json(
        {
          error: {
            code: 'INSUFFICIENT_STOCK',
            message: 'Không đủ tồn kho',
            details: {
              shortages: [
                {
                  product_id: 1,
                  product_name: 'Mì tôm Hảo Hảo',
                  need: '20',
                  have: '5',
                },
              ],
            },
          },
        },
        { status: 400 },
      );
    }
    const paid = body.payments.reduce((s, p) => s + Number(p.amount), 0);
    return HttpResponse.json({
      id: Number(params.id),
      code: 'HD20260523-001',
      customer_id: null,
      customer_name: null,
      cashier_id: 1,
      cashier_name: 'Chủ shop',
      subtotal: 100000,
      discount_amount: 0,
      total: 100000,
      cost_total: 70000,
      paid_amount: paid,
      change_amount: Math.max(0, paid - 100000),
      status: 'COMPLETED',
      note: null,
      completed_at: '2026-05-23T09:00:00Z',
      cancelled_at: null,
      cancel_reason: null,
      created_at: '2026-05-23T08:55:00Z',
      items: [
        {
          id: 1,
          product_id: 1,
          product_name: 'Mì tôm Hảo Hảo',
          product_sku: 'SP000001',
          unit: 'gói',
          quantity: 10,
          unit_price: 10000,
          cost_price: 7000,
          discount_amount: 0,
          line_total: 100000,
        },
      ],
      payments: body.payments.map((p, idx) => ({
        id: idx + 1,
        method: p.method,
        amount: p.amount,
        note: null,
        created_at: '2026-05-23T09:00:00Z',
      })),
    });
  }),
  http.post('*/invoices/:id/cancel', async ({ request, params }) => {
    const body = (await request.json().catch(() => ({}))) as {
      reason?: string;
    };
    return HttpResponse.json({
      id: Number(params.id),
      code: 'HD20260523-001',
      customer_id: null,
      customer_name: null,
      cashier_id: 1,
      cashier_name: 'Chủ shop',
      subtotal: 100000,
      discount_amount: 0,
      total: 100000,
      cost_total: 70000,
      paid_amount: 0,
      change_amount: 0,
      status: 'CANCELLED',
      note: null,
      completed_at: null,
      cancelled_at: '2026-05-23T09:30:00Z',
      cancel_reason: body.reason ?? null,
      created_at: '2026-05-23T08:55:00Z',
      items: [],
      payments: [],
    });
  }),

  http.get('*/inventory', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search');
    const items =
      search === 'EMPTY'
        ? []
        : [
            {
              product_id: 1,
              product_sku: 'SP000001',
              product_name: 'Mì tôm Hảo Hảo',
              unit: 'gói',
              quantity: 3,
              min_stock: 10,
              cost_price: 3500,
              sale_price: 4500,
            },
            {
              product_id: 2,
              product_sku: 'SP000002',
              product_name: 'Coca 330ml',
              unit: 'lon',
              quantity: 50,
              min_stock: 12,
              cost_price: 6000,
              sale_price: 8000,
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

  // ---------- REPORTS ----------
  http.get('*/reports/dashboard', () =>
    HttpResponse.json({
      today_revenue: 1500000,
      today_invoices: 12,
      today_profit: 450000,
      today_customers: 8,
      pending_drafts: 2,
      low_stock_count: 3,
      out_of_stock_count: 1,
      inventory_value: 25000000,
    }),
  ),
  http.get('*/reports/revenue', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-04-23';
    const to = url.searchParams.get('to') ?? '2026-05-23';
    const groupBy = (url.searchParams.get('group_by') ?? 'day') as
      | 'day'
      | 'month';
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      group_by: groupBy,
      total_revenue: 3000000,
      total_profit: 900000,
      total_invoices: 25,
      series: [
        {
          period: '2026-05-21',
          revenue: 1000000,
          invoices: 10,
          profit: 300000,
        },
        {
          period: '2026-05-22',
          revenue: 1200000,
          invoices: 8,
          profit: 360000,
        },
        {
          period: '2026-05-23',
          revenue: 800000,
          invoices: 7,
          profit: 240000,
        },
      ],
    });
  }),
  http.get('*/reports/top-products', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-04-23';
    const to = url.searchParams.get('to') ?? '2026-05-23';
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      items: [
        {
          product_id: 1,
          product_sku: 'SP000001',
          product_name: 'Mì tôm Hảo Hảo',
          quantity_sold: 120,
          revenue: 600000,
          profit: 180000,
        },
        {
          product_id: 2,
          product_sku: 'SP000002',
          product_name: 'Coca 330ml',
          quantity_sold: 80,
          revenue: 560000,
          profit: 140000,
        },
      ],
    });
  }),
  http.get('*/reports/products-sold', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-05-01';
    const to = url.searchParams.get('to') ?? '2026-05-31';
    const page = Number(url.searchParams.get('page') ?? '1');
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      sort_by: url.searchParams.get('sort_by') ?? 'revenue',
      order: url.searchParams.get('order') ?? 'desc',
      category_id: url.searchParams.get('category_id')
        ? Number(url.searchParams.get('category_id'))
        : null,
      items: [
        {
          product_id: 1,
          product_sku: 'SP000001',
          product_name: 'Mì tôm Hảo Hảo',
          quantity_sold: 120,
          revenue: 660000,
          discount: 60000,
          net_revenue: 600000,
          cost: 420000,
          profit: 180000,
          margin_pct: 30,
        },
        {
          product_id: 2,
          product_sku: 'SP000002',
          product_name: 'Coca 330ml',
          quantity_sold: 80,
          revenue: 560000,
          discount: 0,
          net_revenue: 560000,
          cost: 420000,
          profit: 140000,
          margin_pct: 25,
        },
      ],
      totals: {
        quantity_sold: 200,
        revenue: 1220000,
        discount: 60000,
        net_revenue: 1160000,
        cost: 840000,
        profit: 320000,
      },
      pagination: { page, limit: 20, total: 2, total_pages: 1 },
    });
  }),
  http.get('*/reports/profit', ({ request }) => {
    const url = new URL(request.url);
    return HttpResponse.json({
      from_date: url.searchParams.get('from') ?? '2026-04-23',
      to_date: url.searchParams.get('to') ?? '2026-05-23',
      total_revenue: 3000000,
      total_cost: 2100000,
      gross_profit: 900000,
      invoices: 25,
    });
  }),
  http.get('*/reports/stock-summary', () =>
    HttpResponse.json({
      total_products: 50,
      products_in_stock: 45,
      products_out_of_stock: 5,
      low_stock_count: 3,
      total_inventory_value: 25000000,
      last_updated: '2026-05-23T09:00:00Z',
    }),
  ),
  // ---------- CASH BOOK ----------
  http.get('*/cash-transactions', ({ request }) => {
    const url = new URL(request.url);
    const dir = url.searchParams.get('direction');
    const items = [
      {
        id: 1, code: 'PT20260607-001', direction: 'IN', method: 'CASH',
        category: 'CAPITAL', amount: 500000, ref_type: 'MANUAL', ref_id: null,
        partner_type: null, partner_id: null, partner_name: 'Chủ shop',
        note: 'Góp vốn', status: 'ACTIVE', created_at: '2026-06-07T01:00:00Z', created_by: 1,
      },
      {
        id: 2, code: 'PC20260607-001', direction: 'OUT', method: 'CASH',
        category: 'OPERATING', amount: 120000, ref_type: 'MANUAL', ref_id: null,
        partner_type: null, partner_id: null, partner_name: null,
        note: 'Tiền điện', status: 'ACTIVE', created_at: '2026-06-07T02:00:00Z', created_by: 1,
      },
    ].filter((i) => !dir || i.direction === dir);
    return HttpResponse.json({
      items,
      summary: {
        range_in: 500000, range_out: 120000, balance_total: 380000,
        balance_by_method: [{ method: 'CASH', balance: 380000 }],
      },
      pagination: { page: 1, limit: 20, total: items.length, total_pages: 1 },
    });
  }),
  http.post('*/cash-transactions', async ({ request }) => {
    const body = (await request.json()) as { direction: string; method: string; category: string; amount: number };
    return HttpResponse.json(
      {
        id: 99, code: body.direction === 'IN' ? 'PT20260607-099' : 'PC20260607-099',
        direction: body.direction, method: body.method, category: body.category,
        amount: body.amount, ref_type: 'MANUAL', ref_id: null,
        partner_type: null, partner_id: null, partner_name: null, note: null,
        status: 'ACTIVE', created_at: '2026-06-07T03:00:00Z', created_by: 1,
      },
      { status: 201 },
    );
  }),
  http.post('*/cash-transactions/:id/cancel', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id), code: 'PT20260607-001', direction: 'IN', method: 'CASH',
      category: 'CAPITAL', amount: 500000, ref_type: 'MANUAL', ref_id: null,
      partner_type: null, partner_id: null, partner_name: null, note: null,
      status: 'CANCELLED', created_at: '2026-06-07T01:00:00Z', created_by: 1,
    }),
  ),

  // ---------- SALES RETURNS ----------
  http.get('*/returns/returnable/:id', ({ params }) =>
    HttpResponse.json({
      invoice_id: Number(params.id),
      invoice_code: 'HD20260607-001',
      customer_id: null,
      customer_name: null,
      lines: [
        {
          invoice_item_id: 10,
          product_id: 1,
          product_name: 'Coca 330ml',
          product_sku: 'COC',
          unit: 'lon',
          sold_quantity: 5,
          returned_quantity: 0,
          returnable_quantity: 5,
          unit_price: 12000,
        },
      ],
    }),
  ),
  http.get('*/returns', () =>
    HttpResponse.json({
      items: [
        {
          id: 1,
          code: 'TH20260607-001',
          invoice_id: 1,
          customer_name: null,
          total_refund: 24000,
          refund_method: 'CASH',
          status: 'COMPLETED',
          completed_at: '2026-06-07T03:00:00Z',
        },
      ],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    }),
  ),
  http.post('*/returns', () =>
    HttpResponse.json(
      {
        id: 1,
        code: 'TH20260607-001',
        invoice_id: 1,
        customer_id: null,
        customer_name: null,
        total_refund: 24000,
        refund_method: 'CASH',
        status: 'COMPLETED',
        reason: null,
        completed_at: '2026-06-07T03:00:00Z',
        created_at: '2026-06-07T03:00:00Z',
        items: [],
      },
      { status: 201 },
    ),
  ),
];
