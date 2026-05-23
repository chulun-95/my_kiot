import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import InventoryList from '../InventoryList';

describe('InventoryList page', () => {
  it('renders rows from API', async () => {
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
    expect(screen.getByText('SP000002')).toBeInTheDocument();
  });

  it('marks low-stock items with "Sắp hết" badge', async () => {
    render(
      <MemoryRouter>
        <InventoryList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Sắp hết')).toBeInTheDocument();
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
