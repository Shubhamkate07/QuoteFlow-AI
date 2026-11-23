import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../LoadingSpinner';

describe('LoadingSpinner Feedback Component', () => {
  it('renders spinner element with accessible status role', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
  });

  it('renders optional text label', () => {
    render(<LoadingSpinner label="Comparing quotations..." />);
    expect(screen.getByText('Comparing quotations...')).toBeInTheDocument();
  });

  it('applies sizing classes correctly', () => {
    const { rerender } = render(<LoadingSpinner size="sm" />);
    expect(screen.getByRole('status')).toHaveClass('w-4', 'h-4');

    rerender(<LoadingSpinner size="lg" />);
    expect(screen.getByRole('status')).toHaveClass('w-10', 'h-10');
  });
});
