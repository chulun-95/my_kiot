import { useEffect, useState, type InputHTMLAttributes } from 'react';
import { viValidity } from '../utils/validity';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type'
> & {
  value: number;
  onChange: (value: number) => void;
  decimal?: boolean;
};

export default function QtyInput({
  value,
  onChange,
  decimal = false,
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
      step={decimal ? '0.001' : '1'}
      min="0"
      value={text}
      onFocus={(e) => e.currentTarget.select()}
      onChange={(e) => {
        const v = decimal
          ? e.target.value.replace(/[^\d.]/g, '').replace(/(\..*)\./g, '$1')
          : e.target.value.replace(/[^\d]/g, '');
        setText(v);
        if (v === '' || v === '.') return;
        const n = decimal ? parseFloat(v) : parseInt(v, 10);
        if (!Number.isNaN(n)) onChange(n);
      }}
      onBlur={() => {
        const n = decimal ? parseFloat(text) : parseInt(text, 10);
        if (text === '' || Number.isNaN(n)) setText(String(value));
      }}
      className={className}
      {...viValidity({
        rangeUnderflow: 'Số lượng không được nhỏ hơn 0',
        typeMismatch: 'Vui lòng nhập số',
        valueMissing: 'Vui lòng nhập số lượng',
      })}
      {...rest}
    />
  );
}
