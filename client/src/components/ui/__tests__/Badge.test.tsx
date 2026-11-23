import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../Badge';

describe('Badge UI Component', () => {
  it('renders label text', () => {
    render(<Badge>Approved</Badge>);
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('renders status dot when dot prop is true', () => {
    const { container } = render(<Badge dot variant="success">Active</Badge>);
    const dot = container.querySelector('.rounded-full.w-1\\.5');
    expect(dot).toBeInTheDocument();
  });

  it('applies variant styling classes for warning and danger', () => {
    const { rerender } = render(<Badge variant="warning">Pending</Badge>);
    expect(screen.getByText('Pending')).toHaveClass('bg-amber-50', 'text-amber-800');

    rerender(<Badge variant="danger">Critical</Badge>);
    expect(screen.getByText('Critical')).toHaveClass('bg-rose-50', 'text-rose-700');
  });
});
