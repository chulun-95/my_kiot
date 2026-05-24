import { useEffect, useState, type InputHTMLAttributes } from 'react';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'step'
> & {
  value: number;
  onChange: (value: number) => void;
};

export default function QtyInput({
  value,
  onChange,
  className = '',
  ...rest
}: Props) {
  const [text, setText] = useState(String(value));

  useEffect(() => {
    setText(String(value));
  }, [value]);

  return (
    <input
      type="number"
      step="1"
      min="0"
      value={text}
      onFocus={(e) => e.currentTarget.select()}
      onChange={(e) => {
        const v = e.target.value.replace(/[^\d]/g, '');
        setText(v);
        if (v === '') return;
        const n = parseInt(v, 10);
        if (!Number.isNaN(n)) onChange(n);
      }}
      onBlur={() => {
        const n = parseInt(text, 10);
        if (text === '' || Number.isNaN(n)) setText(String(value));
      }}
      className={className}
      {...rest}
    />
  );
}
