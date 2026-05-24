import { useEffect, useRef, useState } from 'react';

interface Props {
  text: string;
  label?: string;
}

export default function FieldHint({ text, label = 'Giải thích' }: Props) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const toggle = (e: { preventDefault: () => void; stopPropagation: () => void }) => {
    e.preventDefault();
    e.stopPropagation();
    setOpen((v) => !v);
  };

  return (
    <span ref={wrapperRef} className="relative inline-block align-middle ml-1">
      <span
        role="button"
        tabIndex={0}
        aria-label={label}
        aria-expanded={open}
        onClick={toggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') toggle(e);
        }}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-200 text-slate-600 text-[10px] font-bold leading-none hover:bg-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer select-none"
      >
        ?
      </span>
      {open && (
        <span
          role="tooltip"
          className="absolute left-0 bottom-full mb-2 w-64 z-20 px-3 py-2 text-xs leading-relaxed text-white bg-slate-800 rounded shadow-lg whitespace-normal"
        >
          {text}
        </span>
      )}
    </span>
  );
}
