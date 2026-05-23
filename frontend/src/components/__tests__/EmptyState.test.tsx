import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EmptyState from '../EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Nothing here yet" />);
    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders action and fires its onClick', () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="Empty"
        action={<button onClick={onClick}>Add</button>}
      />,
    );
    fireEvent.click(screen.getByText('Add'));
    expect(onClick).toHaveBeenCalled();
  });

  it('omits description when not provided', () => {
    render(<EmptyState title="Only title" />);
    expect(screen.getByText('Only title')).toBeInTheDocument();
    expect(screen.queryByText('Nothing here yet')).not.toBeInTheDocument();
  });
});
