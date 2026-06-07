import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EndOfDayPage from '../EndOfDayPage';

describe('EndOfDayPage', () => {
  it('renders per-method balance + sales', async () => {
    render(<MemoryRouter><EndOfDayPage /></MemoryRouter>);
    expect(await screen.findByText('Báo cáo cuối ngày')).toBeInTheDocument();
    expect(await screen.findByText('Tiền mặt')).toBeInTheDocument();
    // tồn cuối tiền mặt 119.000 (there are multiple 119.000, check one is visible)
    expect(screen.getAllByText('119.000 VNĐ').length).toBeGreaterThan(0);
    // doanh thu 24.000
    expect(screen.getAllByText('24.000 VNĐ').length).toBeGreaterThan(0);
  });
});
