import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';

describe('Dashboard page', () => {
  it('renders cards with formatted VND from mock', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Tổng quan')).toBeInTheDocument();
    expect(screen.getByText('Doanh thu hôm nay')).toBeInTheDocument();
    expect(screen.getByText('1.500.000 VNĐ')).toBeInTheDocument();
    expect(screen.getByText('Số hóa đơn hôm nay')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Giá trị tồn kho')).toBeInTheDocument();
    expect(screen.getByText('25.000.000 VNĐ')).toBeInTheDocument();
  });
});
