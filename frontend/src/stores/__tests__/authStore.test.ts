import { beforeEach, describe, expect, it } from 'vitest';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tenant: null, accessToken: null });
  });

  it('starts empty', () => {
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.tenant).toBeNull();
    expect(s.accessToken).toBeNull();
  });

  it('login action sets user/tenant/access token via API', async () => {
    const res = await useAuthStore.getState().login('0900000001', 'secret123');
    expect(res).toBeNull();
    const s = useAuthStore.getState();
    expect(s.user?.id).toBe(1);
    expect(s.tenant?.slug).toBe('shop-a');
    expect(s.accessToken).toBe('access-1');
  });

  it('bootstrap restores session from refresh cookie', async () => {
    await useAuthStore.getState().bootstrap();
    const s = useAuthStore.getState();
    expect(s.accessToken).toBe('access-1');
    expect(s.user?.id).toBe(1);
    expect(s.initializing).toBe(false);
  });

  it('doLogout clears state', async () => {
    useAuthStore.setState({
      user: { id: 1, full_name: 'X', role: 'OWNER' },
      tenant: { id: 1, name: 'Y', slug: 'y' },
      accessToken: 'a',
    });
    await useAuthStore.getState().doLogout();
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
  });

  it('setUser updates only user', () => {
    useAuthStore.setState({ accessToken: 'a' });
    useAuthStore.getState().setUser({ id: 2, full_name: 'Z', role: 'CASHIER' });
    const s = useAuthStore.getState();
    expect(s.user?.id).toBe(2);
    expect(s.accessToken).toBe('a');
  });
});
