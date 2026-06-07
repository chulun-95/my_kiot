import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CashBookList from '../CashBookList';

describe('CashBookList', () => {
  it('renders transactions + balance summary', async () => {
    render(
      <MemoryRouter>
        <CashBookList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Sổ quỹ')).toBeInTheDocument();
    expect(await screen.findByText('PT20260607-001')).toBeInTheDocument();
    expect(screen.getByText('PC20260607-001')).toBeInTheDocument();
    // tồn quỹ hiện tại
    expect(screen.getByText('380.000 VNĐ')).toBeInTheDocument();
  });
});
