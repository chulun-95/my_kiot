import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TopProductsPage from '../TopProductsPage';

describe('TopProductsPage', () => {
  it('renders table rows with SKU + name + revenue', async () => {
    render(
      <MemoryRouter>
        <TopProductsPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText('Top sản phẩm bán chạy'),
    ).toBeInTheDocument();
    expect(await screen.findByText('SP000001')).toBeInTheDocument();
    expect(screen.getAllByText('Mì tôm Hảo Hảo').length).toBeGreaterThan(0);
    expect(screen.getByText('SP000002')).toBeInTheDocument();
    expect(screen.getAllByText('Coca 330ml').length).toBeGreaterThan(0);
    expect(screen.getByText('600.000 VNĐ')).toBeInTheDocument();
    expect(screen.getByText('560.000 VNĐ')).toBeInTheDocument();
  });
});
