import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Login from '../Login';
import { useAuthStore } from '../../../stores/authStore';

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe('Login page', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      tenant: null,
      accessToken: null,
      refreshToken: null,
    });
  });

  it('renders Vietnamese form labels', () => {
    renderLogin();
    expect(screen.getByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument();
    expect(screen.getByText('Số điện thoại')).toBeInTheDocument();
    expect(screen.getByText('Mật khẩu')).toBeInTheDocument();
  });

  it('submits valid credentials and updates auth store', async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '0900000001' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'good123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe('access-1');
    });
  });

  it('shows Vietnamese lockout message on 429', async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '0900000001' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'locked' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('khóa tạm thời');
  });
});
