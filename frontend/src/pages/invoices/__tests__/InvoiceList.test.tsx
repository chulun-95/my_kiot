import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import InvoiceList from '../InvoiceList';

describe('InvoiceList', () => {
  it('renders rows from API', async () => {
    render(
      <MemoryRouter>
        <InvoiceList />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText('HD20260523-001')).toBeInTheDocument(),
    );
    expect(screen.getByText('HD20260523-002')).toBeInTheDocument();
  });

  it('changing status filter triggers refetch (still shows rows for COMPLETED)', async () => {
    render(
      <MemoryRouter>
        <InvoiceList />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByText('HD20260523-001'));
    const select = screen.getByLabelText('Lọc trạng thái') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'COMPLETED' } });
    await waitFor(() => expect(select.value).toBe('COMPLETED'));
    expect(screen.getByText('HD20260523-001')).toBeInTheDocument();
  });
});
