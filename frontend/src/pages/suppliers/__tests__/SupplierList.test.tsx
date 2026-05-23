import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import SupplierList from '../SupplierList';

describe('SupplierList page', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders supplier rows from API', async () => {
    render(
      <MemoryRouter>
        <SupplierList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('NCC Acecook')).toBeInTheDocument();
    expect(screen.getByText('0102030405')).toBeInTheDocument();
  });

  it('has link to /suppliers/new', async () => {
    render(
      <MemoryRouter>
        <SupplierList />
      </MemoryRouter>,
    );
    const link = (await screen.findByText('+ Thêm nhà cung cấp')) as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/suppliers/new');
  });

  it('triggers DELETE /suppliers/:id when Xóa clicked', async () => {
    let called = false;
    server.use(
      http.delete('*/suppliers/:id', () => {
        called = true;
        return HttpResponse.json({ message: 'ok' });
      }),
    );
    render(
      <MemoryRouter>
        <SupplierList />
      </MemoryRouter>,
    );
    const btn = await screen.findByRole('button', { name: 'Xóa' });
    fireEvent.click(btn);
    await waitFor(() => expect(called).toBe(true));
  });
});
