import { useEffect, useRef } from 'react';

type Handler = () => void;
type ShortcutKey = 'F2' | 'F4' | 'F9' | 'Escape';
type ShortcutMap = Partial<Record<ShortcutKey, Handler>>;

interface KeyboardShortcutsOptions {
  enabled?: boolean;
  preventDefault?: boolean;
  ignoreModifier?: boolean;
}

export default function useKeyboardShortcuts(
  map: ShortcutMap,
  options: KeyboardShortcutsOptions = {},
): void {
  const { enabled = true, preventDefault = true, ignoreModifier = true } = options;
  const mapRef = useRef<ShortcutMap>(map);
  mapRef.current = map;

  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (ignoreModifier && (e.ctrlKey || e.metaKey || e.altKey)) return;
      const key = e.key as ShortcutKey;
      const handler = mapRef.current[key];
      if (!handler) return;
      if (preventDefault) e.preventDefault();
      handler();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, preventDefault, ignoreModifier]);
}
