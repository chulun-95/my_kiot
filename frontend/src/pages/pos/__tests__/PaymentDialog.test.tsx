import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PaymentDialog from '../PaymentDialog';

describe('PaymentDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <PaymentDialog
        open={false}
        total={1000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows total prominently and empty cash row by default', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    expect(screen.getByText('Tổng phải trả')).toBeInTheDocument();
    expect(screen.getByText('50.000')).toBeInTheDocument();
    const input = screen.getByLabelText('Tiền khách đưa 1') as HTMLInputElement;
    expect(input.value).toBe('');
    expect(
      screen.getByText(/Để trống nếu khách trả đúng đủ/),
    ).toBeInTheDocument();
  });

  it('empty amount → pay-in-full flag, store uses backend total (no manufactured FE amount)', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={onComplete}
      />,
    );
    fireEvent.click(screen.getByText('Hoàn tất'));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    const [payments, allowDebt, payInFull] = onComplete.mock.calls[0];
    expect(payInFull).toBe(true);
    expect(allowDebt).toBe(false);
    // FE giữ method nhưng KHÔNG tự chế số tiền — store sẽ thay bằng backend total
    expect(payments).toHaveLength(1);
    expect(payments[0].method).toBe('CASH');
    expect(payments[0].amount).toBe(0);
  });

  it('shows change when cashier enters more than total', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    const input = screen.getByLabelText('Tiền khách đưa 1') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '60000' } });
    const changeBox = screen.getByRole('status', {
      name: 'Tiền thừa cho khách',
    });
    expect(changeBox).toHaveTextContent(/Tiền thừa/);
    expect(changeBox).toHaveTextContent('10.000');
  });

  it('shows debt checkbox when cashier types less than total', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    const input = screen.getByLabelText('Tiền khách đưa 1') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '30000' } });
    expect(screen.getByText(/Còn thiếu/)).toBeInTheDocument();
    expect(screen.getByLabelText('Cho phép nợ')).toBeInTheDocument();
  });

  it('multi-row sum includes added row in callback', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={onComplete}
      />,
    );
    fireEvent.change(screen.getByLabelText('Tiền khách đưa 1'), {
      target: { value: '30000' },
    });
    fireEvent.click(screen.getByText('Thêm phương thức'));
    fireEvent.change(screen.getByLabelText('Tiền khách đưa 2'), {
      target: { value: '20000' },
    });
    fireEvent.click(screen.getByText('Hoàn tất'));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    const payments = onComplete.mock.calls[0][0];
    expect(payments).toHaveLength(2);
    expect(payments[0].amount + payments[1].amount).toBe(50000);
  });
});
