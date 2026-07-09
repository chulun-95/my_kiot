import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import InventoryList from '../InventoryList';
import { useAuthStore } from '../../../stores/authStore';

function asOwner() {
  useAuthStore.setState({
    user: { id: 1, full_name: 'Owner', role: 'OWNER', phone: null, email: null },
    tenant: { id: 1, name: 'Shop', slug: 'shop', expires_at: null },
    accessToken: 'tok',
  });
}

function asCashier() {
  useAuthStore.setState({
    user: { id: 2, full_name: 'Cashier', role: 'CASHIER', phone: null, email: null },
    tenant: { id: 1, name: 'Shop', slug: 'shop', expires_at: null },
    accessToken: 'tok',
  });
}

describe('InventoryList page', () => {
  beforeEach(() => {
    asOwner();
  });

  it('renders rows from API', async () => {
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.getByText('SP000002')).toBeInTheDocument();
  });

  it('marks low-stock items with "Sắp hết" badge for OWNER', async () => {
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Sắp hết')).toBeInTheDocument();
  });

  it('hides "Sắp hết" badge and low-stock link for CASHIER', async () => {
    asCashier();
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.queryByText('Sắp hết')).not.toBeInTheDocument();
    expect(screen.queryByText('Xem hàng sắp hết')).not.toBeInTheDocument();
  });

  it('renders empty state', async () => {
    server.use(
      http.get('*/inventory', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText('Chưa có dữ liệu tồn kho'),
    ).toBeInTheDocument();
  });
});
