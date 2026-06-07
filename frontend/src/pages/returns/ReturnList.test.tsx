import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ReturnList from './ReturnList';

describe('ReturnList', () => {
  it('renders return rows', async () => {
    render(
      <MemoryRouter>
        <ReturnList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Trả hàng')).toBeInTheDocument();
    expect(await screen.findByText('TH20260607-001')).toBeInTheDocument();
    expect(screen.getByText('24.000 VNĐ')).toBeInTheDocument();
  });
});
