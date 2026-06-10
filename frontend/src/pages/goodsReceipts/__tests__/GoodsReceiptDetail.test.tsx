import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import GoodsReceiptDetail from '../GoodsReceiptDetail';

function draftReceipt(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    code: 'NK20260608-001',
    status: 'DRAFT',
    supplier_id: null,
    supplier_name: null,
    total: 90000,
    paid_amount: 0,
    note: null,
    created_at: '2026-06-08T03:00:00Z',
    completed_at: null,
    items: [
      {
        id: 1,
        product_id: 1,
        product_sku: 'COC',
        product_name: 'Coca',
        quantity: 10,
        cost_price: 9000,
        line_total: 90000,
      },
    ],
    ...overrides,
  };
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/goods-receipts/7']}>
      <Routes>
        <Route path="/goods-receipts/:id" element={<GoodsReceiptDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('GoodsReceiptDetail — debt requires supplier guard', () => {
  it('blocks completing an unpaid receipt with no supplier and does not call the API', async () => {
    const completeSpy = vi.fn();
    server.use(
      http.get('*/goods-receipts/7', () => HttpResponse.json(draftReceipt())),
      http.post('*/goods-receipts/7/complete', () => {
        completeSpy();
        return HttpResponse.json(draftReceipt({ status: 'COMPLETED' }));
      }),
    );
    renderDetail();

    fireEvent.click(await screen.findByText('Hoàn tất'));
    await waitFor(() =>
      expect(
        screen.getByText(/Nhập nợ phải chọn nhà cung cấp/),
      ).toBeInTheDocument(),
    );
    expect(completeSpy).not.toHaveBeenCalled();
  });

  it('allows completing when a supplier is attached', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const completeSpy = vi.fn();
    server.use(
      http.get('*/goods-receipts/7', () =>
        HttpResponse.json(draftReceipt({ supplier_id: 3, supplier_name: 'NCC X' })),
      ),
      http.post('*/goods-receipts/7/complete', () => {
        completeSpy();
        return HttpResponse.json(
          draftReceipt({ supplier_id: 3, supplier_name: 'NCC X', status: 'COMPLETED' }),
        );
      }),
    );
    renderDetail();

    fireEvent.click(await screen.findByText('Hoàn tất'));
    await waitFor(() => expect(completeSpy).toHaveBeenCalledTimes(1));
  });
});
