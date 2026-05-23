import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkeletonRow, SkeletonCard, SkeletonText } from '../Skeleton';

describe('Skeleton', () => {
  it('SkeletonRow renders N rows', () => {
    render(<SkeletonRow count={3} />);
    expect(screen.getAllByTestId('skeleton-row')).toHaveLength(3);
  });

  it('SkeletonRow defaults to 5 rows', () => {
    render(<SkeletonRow />);
    expect(screen.getAllByTestId('skeleton-row')).toHaveLength(5);
  });

  it('SkeletonCard renders one card', () => {
    render(<SkeletonCard />);
    expect(screen.getByTestId('skeleton-card')).toBeInTheDocument();
  });

  it('SkeletonText renders one text bar', () => {
    render(<SkeletonText width="w-1/2" />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });
});
