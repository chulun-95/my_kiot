import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { useAuthStore } from '../../../stores/authStore';
import ProductForm from '../ProductForm';

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/products/new" element={<ProductForm />} />
        <Route path="/products/:id/edit" element={<ProductForm />} />
        <Route path="/products/:id" element={<div>Detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProductForm', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: { id: 1, full_name: 'Owner', role: 'OWNER' },
      tenant: { id: 1, name: 'Shop', slug: 'shop' },
      accessToken: 't',
      refreshToken: 'r',
    });
  });

  it('create submits and navigates to detail page', async () => {
    renderWithRoute('/products/new');
    const nameInput = await screen.findByLabelText(/Tên sản phẩm/);
    fireEvent.change(nameInput, { target: { value: 'SP mới' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu' }));
    await waitFor(() => expect(screen.getByText('Detail page')).toBeInTheDocument());
  });

  it('edit prefills then PUTs', async () => {
    renderWithRoute('/products/1/edit');
    const nameInput = (await screen.findByDisplayValue('Mì tôm Hảo Hảo')) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: 'Mì tôm sửa' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu' }));
    await waitFor(() => expect(screen.getByText('Detail page')).toBeInTheDocument());
  });

  it('hides cost_price for CASHIER role', async () => {
    useAuthStore.setState({
      user: { id: 2, full_name: 'Cashier', role: 'CASHIER' },
      tenant: { id: 1, name: 'Shop', slug: 'shop' },
      accessToken: 't',
      refreshToken: 'r',
    });
    renderWithRoute('/products/new');
    await screen.findByLabelText(/Tên sản phẩm/);
    expect(screen.queryByText('Giá vốn')).not.toBeInTheDocument();
  });
});
