import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProfitPage from '../ProfitPage';
import RoleGate from '../../../components/RoleGate';
import { useAuthStore } from '../../../stores/authStore';

describe('ProfitPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: 1,
        full_name: 'Owner',
        role: 'OWNER',
        phone: null,
        email: null,
      },
      tenant: { id: 1, name: 'Shop', slug: 'shop' },
      accessToken: 'tok',
      refreshToken: 'r',
    });
  });

  it('renders revenue / cost / profit when loaded', async () => {
    render(
      <MemoryRouter>
        <ProfitPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Báo cáo lợi nhuận')).toBeInTheDocument();
    expect(await screen.findByText('Tổng doanh thu')).toBeInTheDocument();
    expect(screen.getByText('3.000.000 VNĐ')).toBeInTheDocument();
    expect(screen.getByText('2.100.000 VNĐ')).toBeInTheDocument();
    expect(screen.getByText('900.000 VNĐ')).toBeInTheDocument();
    expect(screen.getByText('30.00 %')).toBeInTheDocument();
  });

  it('OwnerOnly wrapper blocks CASHIER', () => {
    useAuthStore.setState({
      user: {
        id: 2,
        full_name: 'Cashier',
        role: 'CASHIER',
        phone: null,
        email: null,
      },
      tenant: { id: 1, name: 'Shop', slug: 'shop' },
      accessToken: 'tok',
      refreshToken: 'r',
    });
    render(
      <MemoryRouter>
        <RoleGate
          allow={['OWNER']}
          fallback={
            <h1 className="text-2xl font-semibold">Không có quyền truy cập</h1>
          }
        >
          <ProfitPage />
        </RoleGate>
      </MemoryRouter>,
    );
    expect(screen.getByText('Không có quyền truy cập')).toBeInTheDocument();
    expect(screen.queryByText('Báo cáo lợi nhuận')).not.toBeInTheDocument();
  });
});
