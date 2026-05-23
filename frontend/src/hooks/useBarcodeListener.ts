import { useEffect, useRef } from 'react';

interface UseBarcodeListenerOptions {
  enabled?: boolean;
  onScan: (code: string) => void;
  minLength?: number;
  burstMs?: number;
}

function isEditableTarget(t: EventTarget | null): boolean {
  if (!t || !(t instanceof HTMLElement)) return false;
  if (
    t.tagName === 'INPUT' ||
    t.tagName === 'TEXTAREA' ||
    t.tagName === 'SELECT'
  ) {
    return true;
  }
  if (t.isContentEditable) return true;
  return false;
}

export function useBarcodeListener({
  enabled = true,
  onScan,
  minLength = 8,
  burstMs = 100,
}: UseBarcodeListenerOptions): void {
  const bufferRef = useRef<string>('');
  const lastTsRef = useRef<number>(0);
  const onScanRef = useRef(onScan);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  useEffect(() => {
    if (!enabled) return;

    function handle(e: KeyboardEvent) {
      if (isEditableTarget(e.target)) return;

      const now = Date.now();
      if (now - lastTsRef.current > burstMs) {
        bufferRef.current = '';
      }
      lastTsRef.current = now;

      if (e.key === 'Enter') {
        const buf = bufferRef.current;
        bufferRef.current = '';
        if (buf.length >= minLength && /^\d+$/.test(buf)) {
          onScanRef.current(buf);
        }
        return;
      }

      if (e.key.length === 1 && /\d/.test(e.key)) {
        bufferRef.current += e.key;
      } else if (e.key.length === 1) {
        // non-digit single char → invalidate
        bufferRef.current = '';
      }
    }

    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [enabled, minLength, burstMs]);
}

export default useBarcodeListener;
