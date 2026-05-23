import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CategoryTree from '../CategoryTree';

describe('CategoryTree page', () => {
  it('renders 2-level tree with parent + child', async () => {
    render(
      <MemoryRouter>
        <CategoryTree />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Đồ ăn')).toBeInTheDocument();
    expect(screen.getByText('Mì gói')).toBeInTheDocument();
    expect(screen.getByText('Đồ uống')).toBeInTheDocument();
  });

  it('disables "+ Thêm con" button on depth-2 child nodes', async () => {
    render(
      <MemoryRouter>
        <CategoryTree />
      </MemoryRouter>,
    );
    await screen.findByText('Mì gói');
    // Two "+ Thêm con" buttons: parent (enabled) for "Đồ ăn" + child (disabled) for "Mì gói"
    const buttons = screen.getAllByRole('button', { name: '+ Thêm con' });
    const disabled = buttons.filter((b) => (b as HTMLButtonElement).disabled);
    expect(disabled.length).toBeGreaterThan(0);
  });

  it('shows "+ Thêm nhóm cha" button', async () => {
    render(
      <MemoryRouter>
        <CategoryTree />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole('button', { name: '+ Thêm nhóm cha' }),
    ).toBeInTheDocument();
  });
});
