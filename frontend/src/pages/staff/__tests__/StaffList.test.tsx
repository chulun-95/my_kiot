import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import StaffList from '../StaffList';

describe('StaffList page', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders staff rows from API', async () => {
    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Nhân viên A')).toBeInTheDocument();
    expect(screen.getByText('CASHIER')).toBeInTheDocument();
  });

  it('triggers PATCH /staff/:id/deactivate when Khóa clicked', async () => {
    let called = false;
    server.use(
      http.patch('*/staff/:id/deactivate', ({ params }) => {
        called = true;
        return HttpResponse.json({
          id: Number(params.id),
          full_name: 'Nhân viên A',
          phone: '0900000002',
          email: null,
          role: 'CASHIER',
          is_active: false,
          last_login_at: null,
          created_at: '2026-05-22T00:00:00Z',
        });
      }),
    );

    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    const btn = await screen.findByRole('button', { name: 'Khóa' });
    fireEvent.click(btn);
    await waitFor(() => expect(called).toBe(true));
  });

  it('shows empty state when API returns no items', async () => {
    server.use(
      http.get('*/staff', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Chưa có nhân viên')).toBeInTheDocument();
  });
});
