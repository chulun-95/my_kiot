import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProductsSoldPage from '../ProductsSoldPage';

describe('ProductsSoldPage', () => {
  it('renders product rows with full columns + totals', async () => {
    render(
      <MemoryRouter>
        <ProductsSoldPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText('Sản phẩm đã bán'),
    ).toBeInTheDocument();
    expect(await screen.findByText('SP000001')).toBeInTheDocument();
    expect(screen.getAllByText('Mì tôm Hảo Hảo').length).toBeGreaterThan(0);
    // doanh thu thuần p1 = 600.000
    expect(screen.getByText('600.000 VNĐ')).toBeInTheDocument();
    // dòng tổng cộng — doanh thu thuần tổng = 1.160.000
    expect(screen.getByText('Tổng cộng')).toBeInTheDocument();
    expect(screen.getByText('1.160.000 VNĐ')).toBeInTheDocument();
  });
});
