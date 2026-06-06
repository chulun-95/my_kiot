import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MoneyInput from './MoneyInput';

function setup(initialValue: number | null | undefined = 0) {
  const onChange = vi.fn();
  const utils = render(
    <MoneyInput value={initialValue} onChange={onChange} aria-label="amount" />,
  );
  const input = screen.getByLabelText('amount') as HTMLInputElement;
  return { input, onChange, ...utils };
}

describe('MoneyInput display', () => {
  it('renders empty string when value=0', () => {
    const { input } = setup(0);
    expect(input.value).toBe('');
  });

  it('renders empty string when value is null', () => {
    const { input } = setup(null);
    expect(input.value).toBe('');
  });

  it('renders empty string when value is undefined', () => {
    const { input } = setup(undefined);
    expect(input.value).toBe('');
  });

  it('formats positive value with vi-VN thousands separator', () => {
    const { input } = setup(5000);
    expect(input.value).toBe('5.000');
  });

  it('renders legacy non-multiple-of-100 value as-is', () => {
    const { input } = setup(12345);
    expect(input.value).toBe('12.345');
  });

  it('treats negative value as empty (defensive)', () => {
    const { input } = setup(-500);
    expect(input.value).toBe('');
  });
});

describe('MoneyInput keyDown digits', () => {
  it('typing "5" from empty → onChange(500)', () => {
    const { input, onChange } = setup(0);
    fireEvent.keyDown(input, { key: '5' });
    expect(onChange).toHaveBeenCalledWith(500);
  });

  it('typing "0" from value=500 → onChange(5000)', () => {
    const { input, onChange } = setup(500);
    fireEvent.keyDown(input, { key: '0' });
    expect(onChange).toHaveBeenCalledWith(5000);
  });

  it('typing "5" from value=500 → onChange(5500)', () => {
    const { input, onChange } = setup(500);
    fireEvent.keyDown(input, { key: '5' });
    expect(onChange).toHaveBeenCalledWith(5500);
  });

  it('typing "0" from value=5000 → onChange(50000)', () => {
    const { input, onChange } = setup(5000);
    fireEvent.keyDown(input, { key: '0' });
    expect(onChange).toHaveBeenCalledWith(50000);
  });

  it('typing letter "a" → onChange NOT called', () => {
    const { input, onChange } = setup(500);
    fireEvent.keyDown(input, { key: 'a' });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('typing digit with Ctrl held (Ctrl+5) → onChange NOT called', () => {
    const { input, onChange } = setup(0);
    fireEvent.keyDown(input, { key: '5', ctrlKey: true });
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('MoneyInput Backspace/Delete', () => {
  it('Backspace at value=500 → onChange(0)', () => {
    const { input, onChange } = setup(500);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('Backspace at value=5000 → onChange(500)', () => {
    const { input, onChange } = setup(5000);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).toHaveBeenCalledWith(500);
  });

  it('Backspace at value=50000 → onChange(5000)', () => {
    const { input, onChange } = setup(50000);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).toHaveBeenCalledWith(5000);
  });

  it('Backspace at value=0 → onChange NOT called', () => {
    const { input, onChange } = setup(0);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('Backspace at legacy value=12345 → onChange(12300)', () => {
    const { input, onChange } = setup(12345);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).toHaveBeenCalledWith(12300);
  });

  it('Delete key behaves like Backspace', () => {
    const { input, onChange } = setup(5000);
    fireEvent.keyDown(input, { key: 'Delete' });
    expect(onChange).toHaveBeenCalledWith(500);
  });
});

describe('MoneyInput paste', () => {
  it('paste "12345" → onChange(12300) (floor to multiple of 100)', () => {
    const { input, onChange } = setup(0);
    fireEvent.paste(input, {
      clipboardData: { getData: () => '12345' },
    });
    expect(onChange).toHaveBeenCalledWith(12300);
  });

  it('paste formatted "12.300" → onChange(12300)', () => {
    const { input, onChange } = setup(0);
    fireEvent.paste(input, {
      clipboardData: { getData: () => '12.300' },
    });
    expect(onChange).toHaveBeenCalledWith(12300);
  });

  it('paste with negative sign "-500" → onChange(500) (sign stripped)', () => {
    const { input, onChange } = setup(0);
    fireEvent.paste(input, {
      clipboardData: { getData: () => '-500' },
    });
    expect(onChange).toHaveBeenCalledWith(500);
  });

  it('paste with no digits "abc" → onChange NOT called (keep current)', () => {
    const { input, onChange } = setup(5000);
    fireEvent.paste(input, {
      clipboardData: { getData: () => 'abc' },
    });
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('MoneyInput onChange fallback (jsdom fireEvent.change / IME)', () => {
  it('fireEvent.change with "60000" → onChange(60000)', () => {
    const { input, onChange } = setup(0);
    fireEvent.change(input, { target: { value: '60000' } });
    expect(onChange).toHaveBeenCalledWith(60000);
  });

  it('fireEvent.change with non-multiple "12345" → onChange(12300) (floor)', () => {
    const { input, onChange } = setup(0);
    fireEvent.change(input, { target: { value: '12345' } });
    expect(onChange).toHaveBeenCalledWith(12300);
  });

  it('fireEvent.change with empty → onChange(0)', () => {
    const { input, onChange } = setup(500);
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(0);
  });
});

describe('MoneyInput disabled', () => {
  it('disabled blocks digit keyDown', () => {
    const onChange = vi.fn();
    render(<MoneyInput value={500} onChange={onChange} disabled aria-label="x" />);
    const input = screen.getByLabelText('x');
    fireEvent.keyDown(input, { key: '5' });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('disabled blocks Backspace', () => {
    const onChange = vi.fn();
    render(<MoneyInput value={500} onChange={onChange} disabled aria-label="x" />);
    const input = screen.getByLabelText('x');
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('MoneyInput cursor', () => {
  it('focus places cursor at end of input', () => {
    const { input } = setup(5000);
    input.focus();
    expect(input.selectionStart).toBe(input.value.length);
    expect(input.selectionEnd).toBe(input.value.length);
  });
});
