import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import GoodsReceiptList from '../GoodsReceiptList';

describe('GoodsReceiptList page', () => {
  it('renders receipts from API', async () => {
    render(
      <MemoryRouter>
        <GoodsReceiptList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('NK20260520-001')).toBeInTheDocument();
    expect(screen.getByText('NK20260521-001')).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(within(table).getByText('NCC Acecook')).toBeInTheDocument();
  });

  it('shows status badges (Hoàn tất / Nháp)', async () => {
    render(
      <MemoryRouter>
        <GoodsReceiptList />
      </MemoryRouter>,
    );
    await screen.findByText('NK20260520-001');
    const table = screen.getByRole('table');
    expect(within(table).getByText('Hoàn tất')).toBeInTheDocument();
    expect(within(table).getByText('Nháp')).toBeInTheDocument();
  });

  it('shows empty state when no receipts', async () => {
    server.use(
      http.get('*/goods-receipts', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <GoodsReceiptList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Chưa có phiếu nhập')).toBeInTheDocument();
  });
});
