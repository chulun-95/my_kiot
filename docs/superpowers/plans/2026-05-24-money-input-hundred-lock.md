# Money Input Hundred-Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the trailing "00" in every money input on the frontend so the minimum unit is 100 VNĐ — user types "5" → display "500", backspace clamps at empty, value emitted is always a non-negative multiple of 100.

**Architecture:** Single-file rewrite of `frontend/src/components/MoneyInput.tsx`. Intercept `onKeyDown` for digits (`onChange(value * 10 + digit * 100)`) and Backspace/Delete (`onChange(Math.floor(value / 1000) * 100)`). Override `onPaste` to floor pasted digits to a multiple of 100. Keep an `onChange` fallback for input events that bypass keyDown (jsdom `fireEvent.change`, IME, mobile autofill). The component's prop signature loses `showZeroAsEmpty`; the only consumer using it is updated.

**Tech Stack:** React 19, TypeScript, Vitest 4, @testing-library/react 16, jsdom.

**Spec:** `docs/superpowers/specs/2026-05-24-money-input-hundred-lock-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/MoneyInput.test.tsx` | Create | Component unit tests covering display, keyDown digits, Backspace/Delete, paste, onChange fallback, disabled, focus cursor |
| `frontend/src/components/MoneyInput.tsx` | Rewrite | New behavior: key interception + paste + onChange fallback + cursor management. Drop `showZeroAsEmpty` prop. |
| `frontend/src/pages/pos/PaymentDialog.tsx` | Modify | Remove obsolete `showZeroAsEmpty` prop at line 228 |
| `frontend/src/pages/pos/__tests__/PaymentDialog.test.tsx` | No change expected | Existing tests use multiples of 100; verify still green |

---

## Task 1: Write failing component tests (RED)

**Files:**
- Create: `frontend/src/components/MoneyInput.test.tsx`

This task lands the full test surface for the new behavior. All tests will fail against the current `MoneyInput.tsx` because it doesn't implement key interception, paste handling, or empty-when-zero display.

- [ ] **Step 1: Create the test file with all behavior tests**

Create `frontend/src/components/MoneyInput.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Run tests to verify they all fail**

Run from `frontend/`:

```powershell
npm test -- --run MoneyInput
```

Expected: many failures because the current component does not implement `onKeyDown`, `onPaste`, the empty-when-0 default display (without `showZeroAsEmpty=true`), or cursor management. Some tests may pass coincidentally (e.g., display formatting tests, since the current `formatter` produces `"5.000"`). That's fine — we just need to confirm the file runs and the bulk of the suite fails.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/components/MoneyInput.test.tsx
git commit -m "test(MoneyInput): add failing tests for hundred-lock behavior"
```

---

## Task 2: Rewrite MoneyInput.tsx (GREEN)

**Files:**
- Modify: `frontend/src/components/MoneyInput.tsx` (full rewrite)

- [ ] **Step 1: Replace MoneyInput.tsx with the new implementation**

Overwrite `frontend/src/components/MoneyInput.tsx` with:

```tsx
import { useLayoutEffect, useRef } from 'react';
import type {
  ChangeEvent,
  ClipboardEvent,
  FocusEvent,
  InputHTMLAttributes,
  KeyboardEvent,
} from 'react';

type Props = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'value' | 'onChange' | 'type' | 'inputMode'
> & {
  value: number | string | null | undefined;
  onChange: (value: number) => void;
  /** Ẩn nhãn "VNĐ" phía bên phải input — dùng khi parent đã đặt ký hiệu ₫ riêng. */
  hideCurrency?: boolean;
};

const formatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

const DIGIT_KEYS = new Set([
  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
]);

const PASSTHROUGH_KEYS = new Set([
  'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
  'Home', 'End', 'Tab', 'Enter', 'Escape', 'Shift',
]);

function normalizeValue(v: number | string | null | undefined): number {
  if (v === null || v === undefined || v === '') return 0;
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.round(n);
}

function toDisplay(v: number): string {
  if (v === 0) return '';
  return formatter.format(v);
}

function floorToHundred(n: number): number {
  return Math.floor(n / 100) * 100;
}

export default function MoneyInput({
  value,
  onChange,
  className = '',
  hideCurrency = false,
  disabled,
  onFocus,
  ...rest
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const numericValue = normalizeValue(value);
  const display = toDisplay(numericValue);

  useLayoutEffect(() => {
    const el = inputRef.current;
    if (el && document.activeElement === el) {
      const end = el.value.length;
      el.setSelectionRange(end, end);
    }
  }, [display]);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    if (DIGIT_KEYS.has(e.key)) {
      e.preventDefault();
      const digit = Number(e.key);
      onChange(numericValue * 10 + digit * 100);
      return;
    }

    if (e.key === 'Backspace' || e.key === 'Delete') {
      e.preventDefault();
      if (numericValue > 0) {
        onChange(Math.floor(numericValue / 1000) * 100);
      }
      return;
    }

    if (PASSTHROUGH_KEYS.has(e.key)) return;

    e.preventDefault();
  }

  function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    if (disabled) return;
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    const digits = text.replace(/\D/g, '');
    if (digits === '') return;
    onChange(floorToHundred(Number(digits)));
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    if (disabled) return;
    const digits = e.target.value.replace(/\D/g, '');
    if (digits === '') {
      onChange(0);
      return;
    }
    onChange(floorToHundred(Number(digits)));
  }

  function handleFocus(e: FocusEvent<HTMLInputElement>) {
    const end = e.currentTarget.value.length;
    e.currentTarget.setSelectionRange(end, end);
    onFocus?.(e);
  }

  return (
    <span className="relative inline-block w-full">
      <input
        {...rest}
        ref={inputRef}
        type="text"
        inputMode="numeric"
        value={display}
        disabled={disabled}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onFocus={handleFocus}
        className={`${className} ${hideCurrency ? '' : 'pr-12'} text-right`}
      />
      {!hideCurrency && (
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 select-none">
          VNĐ
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 2: Run MoneyInput tests and verify all pass**

Run from `frontend/`:

```powershell
npm test -- --run MoneyInput
```

Expected: all tests in `MoneyInput.test.tsx` pass.

If any test fails, fix the implementation. Do NOT relax the test to make it pass. Common debugging pointers:
- "renders empty when value=0" failing → check `toDisplay(0)` returns `""`.
- "Backspace at value=0 → not called" failing → check `if (numericValue > 0)` guard.
- "paste no digits → not called" failing → check `if (digits === '') return;` in `handlePaste`.
- "focus places cursor at end" failing → ensure `handleFocus` calls `setSelectionRange(end, end)`. jsdom supports this.

- [ ] **Step 3: Type-check the change**

```powershell
npm run build
```

Expected: TypeScript compilation succeeds. The `Props` type lost `showZeroAsEmpty` — if `tsc` reports an error in `PaymentDialog.tsx` (line 228 passing `showZeroAsEmpty`), that's the expected next-task signal. Note the error and continue.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/components/MoneyInput.tsx
git commit -m "feat(MoneyInput): lock trailing 00 so min unit is 100 VND

Intercept keyDown for digits and Backspace/Delete to enforce that
the emitted value is always a non-negative multiple of 100. Paste
and onChange fallback floor to the nearest 100. value=0 renders as
empty string (placeholder visible). Drops obsolete showZeroAsEmpty
prop."
```

---

## Task 3: Remove obsolete `showZeroAsEmpty` prop usage

**Files:**
- Modify: `frontend/src/pages/pos/PaymentDialog.tsx:228`

- [ ] **Step 1: Open PaymentDialog.tsx and remove the prop**

In `frontend/src/pages/pos/PaymentDialog.tsx`, remove the `showZeroAsEmpty` line from the `<MoneyInput>` JSX block (currently around line 228):

```diff
                     <MoneyInput
                       value={r.amount}
                       onChange={(v) => updateRow(idx, { amount: v })}
                       aria-label={
                         isCash
                           ? `Tiền khách đưa ${idx + 1}`
                           : `Số tiền ${idx + 1}`
                       }
                       placeholder={isCash ? 'Tiền khách đưa…' : 'Số tiền'}
-                      showZeroAsEmpty
                       hideCurrency
                       autoFocus={idx === 0}
                       className="flex-1 min-w-0 bg-transparent text-right text-xl font-semibold text-slate-900 placeholder:text-slate-300 placeholder:font-normal placeholder:text-[13px] focus:outline-none tabular-nums font-mono"
                     />
```

- [ ] **Step 2: Verify TypeScript compiles**

```powershell
npm run build
```

Expected: build succeeds, no errors about unknown prop `showZeroAsEmpty`.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/pages/pos/PaymentDialog.tsx
git commit -m "refactor(PaymentDialog): drop obsolete showZeroAsEmpty prop"
```

---

## Task 4: Verify full test suite + lint pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend test suite**

```powershell
npm test -- --run
```

Expected: all suites pass. Pay special attention to `PaymentDialog.test.tsx`:
- `'shows total prominently and empty cash row by default'` → asserts `input.value === ''` when value=0. ✓ Matches new behavior.
- `'shows change when cashier enters more than total'` → `fireEvent.change(input, { target: { value: '60000' } })` → expects `60.000` formatted somewhere. With `floor(60000/100)*100 = 60000`, unchanged. ✓
- `'multi-row sum includes added row'` → uses 30000 and 20000 (multiples of 100). ✓

If any PaymentDialog test fails, the change in fire path may have shifted state. Read the failure carefully; do NOT silently update assertions. Common fix: the assertion might be on the formatted string `'60.000'` — verify the new component still renders `'60.000'` for value=60000.

- [ ] **Step 2: Run lint**

```powershell
npm run lint
```

Expected: clean.

If lint complains about an unused import after the rewrite (e.g., a hook not used anymore), remove the import.

- [ ] **Step 3: Manual smoke (record findings, do not commit yet)**

Start the dev server:

```powershell
npm run dev
```

Walk through these flows in a browser (`http://localhost:5173`):

1. **POS — Giảm giá hóa đơn:** focus the discount field, type `5` → see `500`. Type `0` → `5.000`. Backspace → `500`. Backspace → empty.
2. **POS — PaymentDialog (open by clicking Hoàn tất):** in "Tiền khách đưa", type digits. Field starts empty, accepts hundreds only.
3. **POS — CartLine override:** add a product to cart, override its line price; verify hundred-lock.
4. **Sản phẩm — Tạo mới:** open Product form, fill cost_price and sale_price; verify hundred-lock.
5. **Phiếu nhập — Item cost + Tổng đã trả:** verify hundred-lock on both fields.
6. **Legacy data:** if a product with non-multiple-of-100 `cost_price` exists, open the edit form; field displays the exact legacy value; pressing Backspace once normalizes it to floor-100.

If any flow regresses, drop back to Task 2/3 and fix. Do not finalize while a flow is broken.

- [ ] **Step 4: Final cleanup commit (only if there is anything to commit)**

If the smoke test exposed a fix, stage and commit it with a concise message. If nothing to commit, skip.

```powershell
git status
```

Done.

---

## Self-Review Notes (for plan author, not the executor)

- Spec coverage:
  - Display rules (Section 3, "Display" table) → Task 1 display tests
  - Key handlers table → Task 1 keyDown + Backspace tests
  - Paste rules + edge cases → Task 1 paste tests
  - onChange fallback → Task 1 fallback tests
  - Cursor management → Task 1 cursor test + Task 2 implementation
  - Drop `showZeroAsEmpty` → Task 2 (Props type) + Task 3 (consumer)
  - Edge cases (disabled, legacy non-multiple) → Task 1 tests
  - Backend untouched → no task (spec scope confirms)
  - 6 call sites verification → Task 4 Step 3 manual smoke
- Placeholders: none.
- Type consistency: `numericValue: number`, `display: string`, `onChange(value: number)` are consistent across tasks.
