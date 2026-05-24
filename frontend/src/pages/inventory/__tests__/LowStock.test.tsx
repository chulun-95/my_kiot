import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import LowStock from '../LowStock';

describe('LowStock page', () => {
  it('renders rows grouped by severity with summary counts', async () => {
    render(
      <MemoryRouter>
        <LowStock />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Cảnh báo tồn kho')).toBeInTheDocument();
    expect(screen.getByText(/Đã hết hàng — cần nhập gấp/)).toBeInTheDocument();
    expect(screen.getByText(/Sắp hết — đặt hàng sớm/)).toBeInTheDocument();
    expect(screen.getByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.getByText('Coca 330ml')).toBeInTheDocument();
    expect(
      screen.getByText(/1 sản phẩm đã hết hàng/),
    ).toBeInTheDocument();
  });

  it('hides critical section when no out-of-stock items', async () => {
    server.use(
      http.get('*/inventory/low-stock', () =>
        HttpResponse.json({
          items: [
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
          summary: { out_of_stock_count: 0, low_count: 1, total_count: 1 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <LowStock />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.queryByText(/Đã hết hàng — cần nhập gấp/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sản phẩm đã hết hàng/)).not.toBeInTheDocument();
  });

  it('renders empty state when no low-stock items', async () => {
    server.use(
      http.get('*/inventory/low-stock', () =>
        HttpResponse.json({
          items: [],
          summary: { out_of_stock_count: 0, low_count: 0, total_count: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <LowStock />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText(/Không có sản phẩm sắp hết/),
    ).toBeInTheDocument();
  });
});
