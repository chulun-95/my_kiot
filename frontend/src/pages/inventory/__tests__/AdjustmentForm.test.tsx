import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdjustmentForm from '../AdjustmentForm';

describe('AdjustmentForm page', () => {
  it('adds a product row via barcode scan and reflects current stock', async () => {
    render(
      <MemoryRouter>
        <AdjustmentForm />
      </MemoryRouter>,
    );
    const picker = screen.getByLabelText('Tìm sản phẩm hoặc quét mã vạch') as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '8934567890123' } });
    fireEvent.keyDown(picker, { key: 'Enter' });

    expect(await screen.findByText('Sản phẩm quét mã')).toBeInTheDocument();
  });

  it('submits and renders results page', async () => {
    render(
      <MemoryRouter>
        <AdjustmentForm />
      </MemoryRouter>,
    );

    const picker = screen.getByLabelText('Tìm sản phẩm hoặc quét mã vạch') as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '8934567890123' } });
    fireEvent.keyDown(picker, { key: 'Enter' });

    await screen.findByText('Sản phẩm quét mã');

    const qtyInputs = screen.getAllByLabelText(/Tồn mới/);
    fireEvent.change(qtyInputs[0], { target: { value: '15' } });

    fireEvent.click(screen.getByText('Xác nhận điều chỉnh'));

    await waitFor(() =>
      expect(screen.getByText('Kết quả điều chỉnh')).toBeInTheDocument(),
    );
  });

  it('shows validation when no rows', async () => {
    render(
      <MemoryRouter>
        <AdjustmentForm />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Xác nhận điều chỉnh'));
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/sản phẩm/i),
    );
  });
});
