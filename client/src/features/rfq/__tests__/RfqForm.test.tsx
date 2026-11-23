import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RfqForm } from '../components/RfqForm';
import { renderWithProviders } from '../../../test/test-utils';

describe('RfqForm Component and Form Validation', () => {
  it('renders all required form fields in create mode', () => {
    renderWithProviders(
      <RfqForm mode="create" onSubmit={vi.fn()} onCancel={vi.fn()} />
    );

    expect(screen.getByRole('heading', { name: /create new rfq/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/rfq title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rfq number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/currency/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lifecycle status/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save rfq/i })).toBeInTheDocument();
  });

  it('validates minimum title length and blocks submission', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    renderWithProviders(
      <RfqForm mode="create" onSubmit={handleSubmit} onCancel={vi.fn()} />
    );

    // Enter only 1 character
    const titleInput = screen.getByLabelText(/rfq title/i);
    await user.type(titleInput, 'A');
    await user.click(screen.getByRole('button', { name: /save rfq/i }));

    expect(
      await screen.findByText('RFQ title must be at least 3 characters')
    ).toBeInTheDocument();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it('validates RFQ number format if provided', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    renderWithProviders(
      <RfqForm mode="create" onSubmit={handleSubmit} onCancel={vi.fn()} />
    );

    await user.type(screen.getByLabelText(/rfq title/i), 'Valid Machined Enclosures');
    await user.type(screen.getByLabelText(/rfq number/i), 'INVALID-NUMBER-FORMAT');
    await user.click(screen.getByRole('button', { name: /save rfq/i }));

    expect(
      await screen.findByText(/Format must match RFQ-YYYY-XXX/i)
    ).toBeInTheDocument();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it('submits valid form data correctly', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    renderWithProviders(
      <RfqForm mode="create" onSubmit={handleSubmit} onCancel={vi.fn()} />
    );

    await user.type(screen.getByLabelText(/rfq title/i), 'Stainless Steel 316 Valves');
    await user.type(screen.getByLabelText(/rfq number/i), 'RFQ-2026-0099');
    await user.click(screen.getByRole('button', { name: /save rfq/i }));

    // Verify submit handler received valid data
    await vi.waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });
    const submitted = handleSubmit.mock.calls[0][0];
    expect(submitted.title).toBe('Stainless Steel 316 Valves');
    expect(submitted.rfqNumber).toBe('RFQ-2026-0099');
    expect(submitted.currency).toBe('USD');
  });

  it('calls onCancel when Cancel button is clicked', async () => {
    const user = userEvent.setup();
    const handleCancel = vi.fn();
    renderWithProviders(
      <RfqForm mode="create" onSubmit={vi.fn()} onCancel={handleCancel} />
    );

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });
});
