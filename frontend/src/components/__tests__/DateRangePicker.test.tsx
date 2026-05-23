import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DateRangePicker, { defaultRangeLast30 } from '../DateRangePicker';

describe('DateRangePicker', () => {
  it('renders both inputs as controlled', () => {
    const onChange = vi.fn();
    render(
      <DateRangePicker
        value={{ from: '2026-05-01', to: '2026-05-23' }}
        onChange={onChange}
      />,
    );
    const fromInput = screen.getByLabelText('Từ ngày') as HTMLInputElement;
    const toInput = screen.getByLabelText('Đến ngày') as HTMLInputElement;
    expect(fromInput.value).toBe('2026-05-01');
    expect(toInput.value).toBe('2026-05-23');
  });

  it('fires onChange when "from" changes', () => {
    const onChange = vi.fn();
    render(
      <DateRangePicker
        value={{ from: '2026-05-01', to: '2026-05-23' }}
        onChange={onChange}
      />,
    );
    const fromInput = screen.getByLabelText('Từ ngày');
    fireEvent.change(fromInput, { target: { value: '2026-05-10' } });
    expect(onChange).toHaveBeenCalledWith({
      from: '2026-05-10',
      to: '2026-05-23',
    });
  });

  it('shows alert when from > to', () => {
    render(
      <DateRangePicker
        value={{ from: '2026-05-30', to: '2026-05-01' }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole('alert').textContent).toMatch(/không hợp lệ/);
  });

  it('defaultRangeLast30 returns last 30 days span', () => {
    const r = defaultRangeLast30();
    expect(r.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(r.to).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(r.from <= r.to).toBe(true);
  });
});
