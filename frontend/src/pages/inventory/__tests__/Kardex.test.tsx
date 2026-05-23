import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Kardex from '../Kardex';

describe('Kardex page', () => {
  it('renders movements with type labels and signed quantities', async () => {
    render(
      <MemoryRouter initialEntries={['/inventory/1/movements']}>
        <Routes>
          <Route path="/inventory/:productId/movements" element={<Kardex />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Nhập hàng')).toBeInTheDocument();
    expect(screen.getByText('Bán hàng')).toBeInTheDocument();
    expect(screen.getByText('+100')).toBeInTheDocument();
    expect(screen.getByText('-2')).toBeInTheDocument();
  });
});
