import { describe, it, expect } from 'vitest';
import { formatVND, formatDate, formatQty } from '../format';

describe('formatVND', () => {
  it('formats integer with vi-VN thousand separator', () => {
    expect(formatVND(1234567)).toBe('1.234.567 đ');
  });
  it('handles zero, null, undefined, empty string', () => {
    expect(formatVND(0)).toBe('0 đ');
    expect(formatVND(null)).toBe('0 đ');
    expect(formatVND(undefined)).toBe('0 đ');
    expect(formatVND('')).toBe('0 đ');
  });
  it('accepts decimal string and rounds', () => {
    expect(formatVND('1500.50')).toBe('1.501 đ');
  });
  it('returns 0 đ for non-numeric', () => {
    expect(formatVND('abc')).toBe('0 đ');
  });
});

describe('formatQty', () => {
  it('trims trailing zeros', () => {
    expect(formatQty(1.5)).toBe('1.5');
    expect(formatQty(2)).toBe('2');
    expect(formatQty('0.300')).toBe('0.3');
  });
  it('handles null and empty', () => {
    expect(formatQty(null)).toBe('0');
    expect(formatQty('')).toBe('0');
    expect(formatQty(undefined)).toBe('0');
  });
  it('returns 0 for non-numeric', () => {
    expect(formatQty('abc')).toBe('0');
  });
});

describe('formatDate', () => {
  it('formats ISO string to DD/MM/YYYY HH:mm', () => {
    const out = formatDate('2026-05-22T07:30:00Z');
    expect(out).toMatch(/^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}$/);
  });
  it('returns empty for null and invalid', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate(undefined)).toBe('');
    expect(formatDate('not-a-date')).toBe('');
  });
});
