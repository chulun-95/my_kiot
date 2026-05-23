import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StockSummaryPage from '../StockSummaryPage';

describe('StockSummaryPage', () => {
  it('renders tiles with correct numbers and VND', async () => {
    render(
      <MemoryRouter>
        <StockSummaryPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Tổng quan tồn kho')).toBeInTheDocument();
    expect(screen.getByText('Tổng số sản phẩm')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('SP còn hàng')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('SP hết hàng')).toBeInTheDocument();
    expect(screen.getByText('Giá trị tồn kho')).toBeInTheDocument();
    expect(screen.getByText('25.000.000 đ')).toBeInTheDocument();
  });
});
