import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import InvoiceDetail from '../InvoiceDetail';
import { useAuthStore } from '../../../stores/authStore';

function renderAt(role: 'OWNER' | 'CASHIER', userId: number) {
  useAuthStore.setState({
    user: {
      id: userId,
      full_name: 'X',
      role,
      phone: null,
      email: null,
    },
    tenant: { id: 1, name: 'Shop A', slug: 'shop-a' },
    accessToken: 'tok',
  });
  return render(
    <MemoryRouter initialEntries={['/invoices/11']}>
      <Routes>
        <Route path="/invoices/:id" element={<InvoiceDetail />} />
        <Route path="/invoices" element={<div>List</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('InvoiceDetail', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
  });

  it('renders breakdown', async () => {
    renderAt('OWNER', 1);
    await waitFor(() =>
      expect(screen.getByText('HD20260523-001')).toBeInTheDocument(),
    );
    expect(screen.getByText('Mì tôm Hảo Hảo')).toBeInTheDocument();
  });

  it('OWNER sees Cancel button on COMPLETED', async () => {
    renderAt('OWNER', 1);
    await waitFor(() => screen.getByText('HD20260523-001'));
    expect(screen.getByText('Hủy hóa đơn')).toBeInTheDocument();
  });

  it('CASHIER does NOT see Cancel button on COMPLETED', async () => {
    renderAt('CASHIER', 1);
    await waitFor(() => screen.getByText('HD20260523-001'));
    expect(screen.queryByText('Hủy hóa đơn')).toBeNull();
  });
});
