import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import LowStock from '../LowStock';

describe('LowStock page', () => {
  it('renders low-stock rows from API', async () => {
    render(
      <MemoryRouter>
        <LowStock />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
  });

  it('renders empty state when no low-stock items', async () => {
    server.use(
      http.get('*/inventory/low-stock', () =>
        HttpResponse.json({ items: [] }),
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
