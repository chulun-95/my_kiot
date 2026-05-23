import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DraftHoldList from '../DraftHoldList';

describe('DraftHoldList', () => {
  it('renders mocked drafts list', async () => {
    render(<DraftHoldList onRestore={() => {}} onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByText('HD20260523-001')).toBeInTheDocument(),
    );
  });

  it('clicking Khôi phục calls onRestore with full invoice', async () => {
    const onRestore = vi.fn();
    render(<DraftHoldList onRestore={onRestore} onClose={() => {}} />);
    await waitFor(() => screen.getByText('HD20260523-001'));
    fireEvent.click(screen.getByText('Khôi phục'));
    await waitFor(() => expect(onRestore).toHaveBeenCalled());
    const inv = onRestore.mock.calls[0][0];
    expect(inv.code).toBeTruthy();
  });
});
