import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CustomerQuickSearch from '../CustomerQuickSearch';
import type { CustomerResponse } from '../../api/customer';

describe('CustomerQuickSearch', () => {
  it('on Enter with valid phone calls getByPhone and onPick', async () => {
    const picks: Array<CustomerResponse | null> = [];
    render(<CustomerQuickSearch onPick={(c) => picks.push(c)} />);
    const input = screen.getByLabelText('Số điện thoại khách hàng');
    fireEvent.change(input, { target: { value: '0901234567' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(picks.length).toBe(1));
    expect(picks[0]?.id).toBe(50);
  });

  it('on 404 shows create-new fallback form', async () => {
    render(<CustomerQuickSearch onPick={() => {}} />);
    const input = screen.getByLabelText('Số điện thoại khách hàng');
    fireEvent.change(input, { target: { value: '0999999999' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(
      await screen.findByText(/Không tìm thấy/),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Tên khách hàng')).toBeInTheDocument();
  });

  it('Khách vãng lai button calls onPick(null)', async () => {
    const picks: Array<CustomerResponse | null> = [];
    render(<CustomerQuickSearch onPick={(c) => picks.push(c)} />);
    fireEvent.click(screen.getByRole('button', { name: 'Khách vãng lai' }));
    expect(picks).toEqual([null]);
  });

  it('creating new customer after 404 picks created entity', async () => {
    const picks: Array<CustomerResponse | null> = [];
    render(<CustomerQuickSearch onPick={(c) => picks.push(c)} />);
    const input = screen.getByLabelText('Số điện thoại khách hàng');
    fireEvent.change(input, { target: { value: '0999999999' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    const nameInput = await screen.findByPlaceholderText('Tên khách hàng');
    fireEvent.change(nameInput, { target: { value: 'KH mới' } });
    fireEvent.click(screen.getByRole('button', { name: 'Thêm khách mới' }));
    await waitFor(() => expect(picks.length).toBeGreaterThanOrEqual(1));
    const last = picks[picks.length - 1];
    expect(last?.id).toBe(200);
  });
});
