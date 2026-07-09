import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Register from '../Register';
import { useAuthStore } from '../../../stores/authStore';

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  );
}

function fillValidForm() {
  fireEvent.change(screen.getByLabelText('Tên shop'), {
    target: { value: 'Shop A' },
  });
  fireEvent.change(screen.getByLabelText('Số điện thoại'), {
    target: { value: '0900000001' },
  });
  fireEvent.change(screen.getByLabelText('Địa chỉ'), {
    target: { value: '123 Đường ABC, Quận 1' },
  });
  fireEvent.change(screen.getByLabelText('Mật khẩu'), {
    target: { value: 'secret1' },
  });
  fireEvent.change(screen.getByLabelText('Nhập lại mật khẩu'), {
    target: { value: 'secret1' },
  });
}

describe('Register page', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      tenant: null,
      accessToken: null,
    });
  });

  it('renders Vietnamese form labels', () => {
    renderRegister();
    expect(screen.getByText('Đăng ký shop mới')).toBeInTheDocument();
    expect(screen.getByText('Tên shop')).toBeInTheDocument();
    expect(screen.getByText('Địa chỉ')).toBeInTheDocument();
    expect(screen.getByText('Nhập lại mật khẩu')).toBeInTheDocument();
    expect(screen.queryByText('Tên chủ shop')).not.toBeInTheDocument();
    expect(screen.queryByText(/^Email/)).not.toBeInTheDocument();
  });

  it('submits and dispatches register, populating store', async () => {
    renderRegister();
    fillValidForm();
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe('access-1');
    });
  });

  it('rejects invalid phone format client-side', async () => {
    renderRegister();
    fillValidForm();
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('10 chữ số');
  });

  it('requires address to be filled', () => {
    renderRegister();
    const addressField = screen.getByLabelText('Địa chỉ') as HTMLTextAreaElement;
    expect(addressField.required).toBe(true);
  });

  it('rejects mismatched confirm password client-side', async () => {
    renderRegister();
    fillValidForm();
    fireEvent.change(screen.getByLabelText('Nhập lại mật khẩu'), {
      target: { value: 'khac-mat-khau' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Xác nhận mật khẩu không khớp');
    // Không gọi API khi mismatch — store vẫn giữ trạng thái chưa đăng nhập
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
