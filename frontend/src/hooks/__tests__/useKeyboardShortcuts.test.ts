import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import useKeyboardShortcuts from '../useKeyboardShortcuts';

function fireKey(key: string, init: Partial<KeyboardEventInit> = {}) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, ...init }));
}

describe('useKeyboardShortcuts', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('triggers F2 handler', () => {
    const onF2 = vi.fn();
    renderHook(() => useKeyboardShortcuts({ F2: onF2 }));
    fireKey('F2');
    expect(onF2).toHaveBeenCalledOnce();
  });

  it('triggers Escape handler', () => {
    const onEsc = vi.fn();
    renderHook(() => useKeyboardShortcuts({ Escape: onEsc }));
    fireKey('Escape');
    expect(onEsc).toHaveBeenCalledOnce();
  });

  it('ignores modifier+key combos by default', () => {
    const onF2 = vi.fn();
    renderHook(() => useKeyboardShortcuts({ F2: onF2 }));
    fireKey('F2', { ctrlKey: true });
    expect(onF2).not.toHaveBeenCalled();
  });

  it('suppresses all keys when enabled=false', () => {
    const onF2 = vi.fn();
    renderHook(() =>
      useKeyboardShortcuts({ F2: onF2 }, { enabled: false }),
    );
    fireKey('F2');
    expect(onF2).not.toHaveBeenCalled();
  });

  it('removes listener on unmount', () => {
    const onF2 = vi.fn();
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts({ F2: onF2 }),
    );
    unmount();
    fireKey('F2');
    expect(onF2).not.toHaveBeenCalled();
  });
});
