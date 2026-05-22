import { describe, it, expect } from 'vitest';
import { extractApiError, friendlyMessage, toFriendlyMessage } from '../errors';

describe('extractApiError', () => {
  it('parses axios-shaped error', () => {
    const err = {
      isAxiosError: true,
      response: { data: { error: { code: 'INSUFFICIENT_STOCK', message: 'X' } } },
    };
    const parsed = extractApiError(err);
    expect(parsed?.code).toBe('INSUFFICIENT_STOCK');
    expect(parsed?.message).toBe('X');
  });
  it('returns null for null, plain Error, and unknown shapes', () => {
    expect(extractApiError(null)).toBeNull();
    expect(extractApiError(new Error('boom'))).toBeNull();
    expect(extractApiError({ response: { data: {} } })).toBeNull();
    expect(extractApiError({ response: { data: { error: null } } })).toBeNull();
  });
});

describe('friendlyMessage', () => {
  it('maps known codes to Vietnamese', () => {
    expect(friendlyMessage('INSUFFICIENT_STOCK')).toBe('Số lượng tồn không đủ');
    expect(friendlyMessage('INVALID_CREDENTIALS')).toBe('Sai số điện thoại hoặc mật khẩu');
    expect(friendlyMessage('ACCOUNT_LOCKED')).toBe(
      'Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau',
    );
    expect(friendlyMessage('FORBIDDEN')).toBe('Bạn không có quyền thực hiện thao tác này');
  });
  it('falls back to provided fallback for unknown codes', () => {
    expect(friendlyMessage('UNKNOWN_CODE', 'Custom')).toBe('Custom');
  });
  it('falls back to default for unknown codes with no fallback', () => {
    expect(friendlyMessage('UNKNOWN_CODE')).toBe('Có lỗi xảy ra, vui lòng thử lại');
  });
});

describe('toFriendlyMessage', () => {
  it('uses extracted code mapping when available', () => {
    const err = {
      isAxiosError: true,
      response: { data: { error: { code: 'DUPLICATE_PHONE', message: 'dup' } } },
    };
    expect(toFriendlyMessage(err)).toBe('Số điện thoại đã tồn tại');
  });
  it('falls back to plain Error message when no fallback supplied', () => {
    expect(toFriendlyMessage(new Error('boom'))).toBe('boom');
  });
  it('uses fallback for unknown shapes', () => {
    expect(toFriendlyMessage({}, 'fb')).toBe('fb');
  });
  it('uses default when nothing else available', () => {
    expect(toFriendlyMessage({})).toBe('Có lỗi xảy ra, vui lòng thử lại');
  });
});
