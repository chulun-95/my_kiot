import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import CustomerList from '../CustomerList';

describe('CustomerList page', () => {
  it('renders customer rows from API', async () => {
    render(
      <MemoryRouter>
        <CustomerList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Nguyễn Văn A')).toBeInTheDocument();
    expect(screen.getByText('0901234567')).toBeInTheDocument();
  });

  it('sends search param when user types', async () => {
    let receivedSearch: string | null = null;
    server.use(
      http.get('*/customers', ({ request }) => {
        const url = new URL(request.url);
        receivedSearch = url.searchParams.get('search');
        return HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        });
      }),
    );
    render(
      <MemoryRouter>
        <CustomerList />
      </MemoryRouter>,
    );
    const input = await screen.findByPlaceholderText('Tìm theo tên hoặc SĐT...');
    fireEvent.change(input, { target: { value: 'Nguyễn' } });
    await waitFor(() => expect(receivedSearch).toBe('Nguyễn'));
  });

  it('shows empty state', async () => {
    server.use(
      http.get('*/customers', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <CustomerList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Chưa có khách hàng')).toBeInTheDocument();
  });
});
