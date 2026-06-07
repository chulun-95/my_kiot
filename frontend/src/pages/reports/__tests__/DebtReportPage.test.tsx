import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DebtReportPage from '../DebtReportPage';

describe('DebtReportPage', () => {
  it('renders customer + supplier debts', async () => {
    render(
      <MemoryRouter>
        <DebtReportPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Báo cáo công nợ')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn A')).toBeInTheDocument();
    });
    expect(screen.getByText('NCC X')).toBeInTheDocument();
    expect(screen.getByText('14.000 VNĐ')).toBeInTheDocument();
  });
});
