import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import CashVoucherForm from '../CashVoucherForm';

function renderForm() {
  return render(
    <MemoryRouter initialEntries={['/cash-book/new']}>
      <Routes>
        <Route path="/cash-book/new" element={<CashVoucherForm />} />
        <Route path="/cash-book" element={<div>Sổ quỹ list</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CashVoucherForm', () => {
  it('creates a receipt then navigates back to list', async () => {
    renderForm();
    await screen.findByText('Lập phiếu thu/chi');
    fireEvent.change(screen.getByLabelText('Số tiền'), { target: { value: '150000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu phiếu' }));
    await waitFor(() => expect(screen.getByText('Sổ quỹ list')).toBeInTheDocument());
  });
});
