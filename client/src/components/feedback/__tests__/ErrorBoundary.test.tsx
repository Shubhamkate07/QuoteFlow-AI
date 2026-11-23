import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorBoundary } from '../ErrorBoundary';

const BombComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Explosion in procurement rendering pipeline!');
  }
  return <div>Component loaded normally</div>;
};

describe('ErrorBoundary Component', () => {
  const originalConsoleError = console.error;

  beforeEach(() => {
    // Suppress console.error in JSDOM during expected boundary errors
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <BombComponent shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Component loaded normally')).toBeInTheDocument();
  });

  it('catches render errors and displays fallback UI', () => {
    render(
      <ErrorBoundary>
        <BombComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(
      screen.getByText(/an unexpected application error occurred while rendering this view/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Explosion in procurement rendering pipeline!')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload application/i })).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom Error Screen</div>}>
        <BombComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error Screen')).toBeInTheDocument();
  });

  it('calls window.location.reload when Reload Application button is clicked', async () => {
    const user = userEvent.setup();
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, reload: reloadMock },
    });

    render(
      <ErrorBoundary>
        <BombComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    await user.click(screen.getByRole('button', { name: /reload application/i }));
    expect(reloadMock).toHaveBeenCalledTimes(1);
  });
});
