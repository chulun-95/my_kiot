import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import ProductList from '../ProductList';

describe('ProductList page', () => {
  it('renders product rows from API', async () => {
    render(
      <MemoryRouter>
        <ProductList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.getByText('SP000001')).toBeInTheDocument();
  });

  it('shows empty state when no items', async () => {
    server.use(
      http.get('*/products', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <ProductList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Chưa có sản phẩm')).toBeInTheDocument();
  });

  it('renders status filter options', async () => {
    render(
      <MemoryRouter>
        <ProductList />
      </MemoryRouter>,
    );
    await screen.findByText('Mì tôm Hảo Hảo');
    expect(screen.getByRole('option', { name: 'Đang bán' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Ngừng bán' })).toBeInTheDocument();
  });
});
