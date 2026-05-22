import { describe, it, expect } from 'vitest';
import * as authApi from '../auth';

describe('auth API', () => {
  it('login returns user/tenant/tokens', async () => {
    const res = await authApi.login({ phone: '0900000001', password: 'good' });
    expect('user' in res).toBe(true);
    if ('user' in res) {
      expect(res.user.id).toBe(1);
      expect(res.tenant.slug).toBe('shop-a');
    }
  });

  it('login surfaces 429 lockout as axios error', async () => {
    await expect(
      authApi.login({ phone: '0900000001', password: 'locked' }),
    ).rejects.toMatchObject({
      response: { status: 429 },
    });
  });

  it('register returns auth payload', async () => {
    const res = await authApi.register({
      shop_name: 'S',
      owner_name: 'O',
      phone: '0922222222',
      password: 'secret1',
    });
    expect(res.access_token).toBe('access-1');
  });

  it('me returns user + tenant', async () => {
    const res = await authApi.me();
    expect(res.user.id).toBe(1);
  });

  it('changePassword returns new token pair', async () => {
    const res = await authApi.changePassword({
      current_password: 'old',
      new_password: 'newsecret',
      confirm_password: 'newsecret',
    });
    expect(res.access_token).toBe('new-access');
  });
});
