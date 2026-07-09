import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import POSScreen from '../POSScreen';
import { useAuthStore } from '../../../stores/authStore';
import { usePosStore } from '../../../stores/posStore';

function setupAuth() {
  useAuthStore.setState({
    user: { id: 1, full_name: 'Chủ shop', role: 'OWNER', phone: null, email: null },
    tenant: { id: 1, name: 'Shop A', slug: 'shop-a', expires_at: null },
    accessToken: 'tok',
  });
}

describe('POSScreen', () => {
  beforeEach(() => {
    setupAuth();
    usePosStore.getState().reset();
    usePosStore.setState({ lastCompleted: null });
  });

  it('renders empty cart placeholder', () => {
    render(
      <MemoryRouter>
        <POSScreen />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(/Giỏ trống. Quét mã hoặc tìm sản phẩm/i),
    ).toBeInTheDocument();
  });

  it('adds product via ProductPicker barcode', async () => {
    render(
      <MemoryRouter>
        <POSScreen />
      </MemoryRouter>,
    );
    const picker = screen.getByLabelText(
      'Tìm sản phẩm hoặc quét mã vạch',
    ) as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '8934567890123' } });
    fireEvent.keyDown(picker, { key: 'Enter' });
    expect(await screen.findByText('Sản phẩm quét mã')).toBeInTheDocument();
  });

  it('Thanh toán button disabled with empty cart', () => {
    render(
      <MemoryRouter>
        <POSScreen />
      </MemoryRouter>,
    );
    expect(screen.getByText('Thanh toán')).toBeDisabled();
  });

  it('opens PaymentDialog when clicking Thanh toán with items', async () => {
    act(() => {
      usePosStore.getState().addItem({
        id: 1,
        sku: 'SP000001',
        barcode: null,
        name: 'Mì tôm',
        unit: 'gói',
        sale_price: 5000,
        cost_price: 3500,
        image_url: null,
        allow_negative: false,
        status: 'ACTIVE',
      });
    });
    render(
      <MemoryRouter>
        <POSScreen />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Thanh toán'));
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: 'Thanh toán' })).toBeInTheDocument(),
    );
  });
});
