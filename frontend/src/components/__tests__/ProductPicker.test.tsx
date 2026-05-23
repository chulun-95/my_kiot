import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ProductPicker from '../ProductPicker';
import type { ProductBrief } from '../../api/product';

describe('ProductPicker', () => {
  it('barcode (numeric, length >= 6) on Enter triggers barcode lookup + onPick', async () => {
    const picked: ProductBrief[] = [];
    render(<ProductPicker onPick={(p) => picked.push(p)} />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '8934567890123' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(picked.length).toBe(1));
    expect(picked[0].id).toBe(11);
  });

  it('text query opens dropdown with search results', async () => {
    vi.useFakeTimers();
    const picked: ProductBrief[] = [];
    render(<ProductPicker onPick={(p) => picked.push(p)} />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'mì' } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();
    expect(await screen.findByText(/Kết quả mì/)).toBeInTheDocument();
  });

  it('shows error message when barcode not found', async () => {
    render(<ProductPicker onPick={() => {}} />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '0000000000000' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/Không tìm thấy|Mã/i),
    );
  });
});
