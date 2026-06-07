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
  });

  it('submits and dispatches register, populating store', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText('Tên shop'), {
      target: { value: 'Shop A' },
    });
    fireEvent.change(screen.getByLabelText('Tên chủ shop'), {
      target: { value: 'Chủ shop' },
    });
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '0900000001' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'secret1' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe('access-1');
    });
  });

  it('rejects invalid phone format client-side', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText('Tên shop'), {
      target: { value: 'Shop A' },
    });
    fireEvent.change(screen.getByLabelText('Tên chủ shop'), {
      target: { value: 'Chủ shop' },
    });
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '123' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'secret1' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('10 chữ số');
  });
});
