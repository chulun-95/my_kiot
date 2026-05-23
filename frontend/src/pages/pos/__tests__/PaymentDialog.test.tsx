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

  it('starts with one CASH row matching total', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    const input = screen.getByLabelText('Số tiền 1') as HTMLInputElement;
    expect(input.value).toBe('50000');
  });

  it('shows change when overpaying', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    const input = screen.getByLabelText('Số tiền 1') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '60000' } });
    expect(screen.getByText(/Tiền thừa/)).toBeInTheDocument();
  });

  it('shows debt checkbox when underpaying', () => {
    render(
      <PaymentDialog
        open
        total={50000}
        onClose={() => {}}
        onComplete={async () => {}}
      />,
    );
    const input = screen.getByLabelText('Số tiền 1') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '30000' } });
    expect(screen.getByText(/Còn thiếu/)).toBeInTheDocument();
    expect(screen.getByLabelText('Cho phép nợ')).toBeInTheDocument();
  });

  it('complete fires callback with payments rows', async () => {
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
    const [payments, allowDebt] = onComplete.mock.calls[0];
    expect(payments[0].method).toBe('CASH');
    expect(payments[0].amount).toBe(50000);
    expect(allowDebt).toBe(false);
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
    fireEvent.change(screen.getByLabelText('Số tiền 1'), {
      target: { value: '30000' },
    });
    fireEvent.click(screen.getByText('+ Thêm phương thức'));
    fireEvent.change(screen.getByLabelText('Số tiền 2'), {
      target: { value: '20000' },
    });
    fireEvent.click(screen.getByText('Hoàn tất'));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    const payments = onComplete.mock.calls[0][0];
    expect(payments).toHaveLength(2);
    expect(payments[0].amount + payments[1].amount).toBe(50000);
  });
});
