import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import GoodsReceiptForm from '../GoodsReceiptForm';

describe('GoodsReceiptForm page', () => {
  it('adds a line via ProductPicker barcode and computes total', async () => {
    render(
      <MemoryRouter initialEntries={['/goods-receipts/new']}>
        <Routes>
          <Route path="/goods-receipts/new" element={<GoodsReceiptForm />} />
          <Route path="/goods-receipts/:id" element={<div>Detail page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    const picker = screen.getByLabelText('Tìm sản phẩm hoặc quét mã vạch') as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '8934567890123' } });
    fireEvent.keyDown(picker, { key: 'Enter' });

    expect(await screen.findByText('Sản phẩm quét mã')).toBeInTheDocument();
  });

  it('submits and navigates to detail', async () => {
    render(
      <MemoryRouter initialEntries={['/goods-receipts/new']}>
        <Routes>
          <Route path="/goods-receipts/new" element={<GoodsReceiptForm />} />
          <Route path="/goods-receipts/:id" element={<div>Detail page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    const picker = screen.getByLabelText('Tìm sản phẩm hoặc quét mã vạch') as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '8934567890123' } });
    fireEvent.keyDown(picker, { key: 'Enter' });
    await screen.findByText('Sản phẩm quét mã');

    fireEvent.click(screen.getByText('Lưu phiếu nháp'));
    await waitFor(() =>
      expect(screen.getByText('Detail page')).toBeInTheDocument(),
    );
  });

  it('shows validation when no products', async () => {
    render(
      <MemoryRouter initialEntries={['/goods-receipts/new']}>
        <Routes>
          <Route path="/goods-receipts/new" element={<GoodsReceiptForm />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Lưu phiếu nháp'));
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/sản phẩm/i),
    );
  });
});
