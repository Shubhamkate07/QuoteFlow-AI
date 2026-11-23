import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../Button';

describe('Button UI Component', () => {
  it('renders children text correctly', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('handles click events when not disabled', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Submit</Button>);

    await user.click(screen.getByRole('button', { name: /submit/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not trigger onClick when disabled', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Disabled</Button>);

    const button = screen.getByRole('button', { name: /disabled/i });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('renders loading spinner and disables button when isLoading is true', () => {
    render(<Button isLoading>Save Changes</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    // Child text is present alongside spinner
    expect(button).toHaveTextContent(/save changes/i);
    // Spinner element is present
    expect(button.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('applies variant styling classes properly', () => {
    const { rerender } = render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-rose-600');

    rerender(<Button variant="outline">Outline</Button>);
    expect(screen.getByRole('button')).toHaveClass('border-slate-300');

    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-slate-100');
  });

  it('renders left and right icons appropriately', () => {
    render(
      <Button
        leftIcon={<span data-testid="left-icon">←</span>}
        rightIcon={<span data-testid="right-icon">→</span>}
      >
        Navigation
      </Button>
    );

    expect(screen.getByTestId('left-icon')).toBeInTheDocument();
    expect(screen.getByTestId('right-icon')).toBeInTheDocument();
  });
});
