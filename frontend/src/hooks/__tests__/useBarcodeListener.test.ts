import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useBarcodeListener } from '../useBarcodeListener';

function pressKey(key: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }));
}

describe('useBarcodeListener', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('recognizes a fast digit burst followed by Enter', () => {
    const onScan = vi.fn();
    renderHook(() => useBarcodeListener({ onScan, minLength: 8 }));

    const code = '8934567890123';
    for (const ch of code) {
      pressKey(ch);
    }
    pressKey('Enter');

    expect(onScan).toHaveBeenCalledWith(code);
  });

  it('ignores slow typing (gap > burstMs)', () => {
    const onScan = vi.fn();
    renderHook(() => useBarcodeListener({ onScan, minLength: 8, burstMs: 50 }));

    pressKey('1');
    vi.advanceTimersByTime(200);
    pressKey('2');
    pressKey('Enter');

    expect(onScan).not.toHaveBeenCalled();
  });

  it('ignores keystrokes from input elements', () => {
    const onScan = vi.fn();
    renderHook(() => useBarcodeListener({ onScan, minLength: 4 }));

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    for (const ch of '12345678') {
      input.dispatchEvent(
        new KeyboardEvent('keydown', { key: ch, bubbles: true }),
      );
    }
    input.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    );

    expect(onScan).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it('does not fire when buffer is shorter than minLength', () => {
    const onScan = vi.fn();
    renderHook(() => useBarcodeListener({ onScan, minLength: 8 }));

    pressKey('1');
    pressKey('2');
    pressKey('3');
    pressKey('Enter');

    expect(onScan).not.toHaveBeenCalled();
  });
});
