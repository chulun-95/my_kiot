import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import GoodsReceiptForm from '../GoodsReceiptForm';
import { server } from '../../../__tests__/setup';

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

  it('sends selected payment_method when paid', async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.post('*/goods-receipts', async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 99 }, { status: 201 });
      }),
    );

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

    // tick "Thanh toán đủ" để paid > 0 → hiện ô phương thức
    fireEvent.click(screen.getByLabelText('Thanh toán đủ'));
    const methodSelect = await screen.findByLabelText('Phương thức thanh toán');
    fireEvent.change(methodSelect, { target: { value: 'BANK_TRANSFER' } });

    fireEvent.click(screen.getByText('Lưu phiếu nháp'));
    await waitFor(() => expect(screen.getByText('Detail page')).toBeInTheDocument());
    expect(captured).not.toBeNull();
    expect(captured!.payment_method).toBe('BANK_TRANSFER');
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
