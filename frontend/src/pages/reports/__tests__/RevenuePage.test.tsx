import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RevenuePage from '../RevenuePage';
import * as reportApi from '../../../api/report';

describe('RevenuePage', () => {
  it('renders summary tiles after load', async () => {
    render(
      <MemoryRouter>
        <RevenuePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Tổng doanh thu')).toBeInTheDocument();
    expect(screen.getAllByText('3.000.000 VNĐ').length).toBeGreaterThan(0);
    expect(screen.getByText('Tổng lợi nhuận')).toBeInTheDocument();
    expect(screen.getByText('900.000 VNĐ')).toBeInTheDocument();
  });

  it('clicking "Xem báo cáo" re-fetches with current params', async () => {
    const spy = vi.spyOn(reportApi, 'getRevenue');

    render(
      <MemoryRouter>
        <RevenuePage />
      </MemoryRouter>,
    );
    await screen.findByText('Tổng doanh thu');
    const initialCalls = spy.mock.calls.length;

    fireEvent.change(screen.getByLabelText('Nhóm theo'), {
      target: { value: 'month' },
    });
    fireEvent.click(screen.getByText('Xem báo cáo'));

    await waitFor(() => {
      expect(spy.mock.calls.length).toBeGreaterThan(initialCalls);
    });
    const lastCall = spy.mock.calls.at(-1);
    expect(lastCall?.[0].group_by).toBe('month');

    spy.mockRestore();
  });

  it('renders chart container', async () => {
    render(
      <MemoryRouter>
        <RevenuePage />
      </MemoryRouter>,
    );
    await screen.findByText('Tổng doanh thu');
    expect(screen.getByTestId('revenue-chart')).toBeInTheDocument();
  });
});
