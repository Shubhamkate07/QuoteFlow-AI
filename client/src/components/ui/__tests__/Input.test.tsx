import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../Input';

describe('Input UI Component', () => {
  it('renders label and input element', () => {
    render(<Input label="Company Name" placeholder="Enter company" />);
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter company/i)).toBeInTheDocument();
  });

  it('indicates required status with asterisk', () => {
    render(<Input label="Work Email" required />);
    expect(screen.getByText('*')).toHaveClass('text-rose-500');
  });

  it('displays validation error message when provided', () => {
    render(<Input label="Email" error="Invalid email address" />);
    expect(screen.getByText('Invalid email address')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveClass('border-rose-400');
  });

  it('displays helper text when no error is present', () => {
    render(<Input label="Target Budget" helperText="Include currency symbol" />);
    expect(screen.getByText('Include currency symbol')).toBeInTheDocument();
  });

  it('accepts typing input via user event', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Input label="RFQ Number" onChange={handleChange} />);

    const input = screen.getByLabelText(/rfq number/i);
    await user.type(input, 'RFQ-2026-001');

    expect(input).toHaveValue('RFQ-2026-001');
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders disabled input state correctly', () => {
    render(<Input label="Locked Field" disabled value="Fixed Value" readOnly />);
    const input = screen.getByLabelText(/locked field/i);
    expect(input).toBeDisabled();
    expect(input).toHaveClass('disabled:bg-slate-50');
  });

  it('renders left and right icons correctly', () => {
    render(
      <Input
        label="Search"
        leftIcon={<span data-testid="search-icon">🔍</span>}
        rightIcon={<span data-testid="clear-icon">✕</span>}
      />
    );
    expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    expect(screen.getByTestId('clear-icon')).toBeInTheDocument();
  });
});
