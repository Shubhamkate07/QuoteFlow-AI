import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupplierForm } from '../components/SupplierForm';
import { renderWithProviders } from '../../../test/test-utils';

describe('SupplierForm Validation and Submission', () => {
  it('renders all required supplier registration inputs', () => {
    renderWithProviders(
      <SupplierForm mode="create" onSubmit={vi.fn()} onCancel={vi.fn()} />
    );

    expect(screen.getByRole('heading', { name: /register new supplier/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/primary contact person/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/business email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/physical facility/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/primary manufacturing category/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register supplier/i })).toBeInTheDocument();
  });

  it('validates invalid email format and blocks submission', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    renderWithProviders(
      <SupplierForm mode="create" onSubmit={handleSubmit} onCancel={vi.fn()} />
    );

    await user.type(screen.getByLabelText(/company name/i), 'Apex Fasteners');
    await user.type(screen.getByLabelText(/primary contact person/i), 'John Doe');
    await user.type(screen.getByLabelText(/business email/i), 'not-an-email');
    await user.type(screen.getByLabelText(/phone number/i), '+1555123456');
    await user.type(screen.getByLabelText(/physical facility/i), '123 Industrial Park');

    // Trigger form submit
    const submitBtn = screen.getByRole('button', { name: /register supplier/i });
    fireEvent.submit(submitBtn.closest('form')!);

    expect(
      await screen.findByText('Please enter a valid email address')
    ).toBeInTheDocument();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it('submits valid supplier profile successfully', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    renderWithProviders(
      <SupplierForm mode="create" onSubmit={handleSubmit} onCancel={vi.fn()} />
    );

    await user.type(screen.getByLabelText(/company name/i), 'Apex Fasteners Corp');
    await user.type(screen.getByLabelText(/primary contact person/i), 'Alice Walker');
    await user.type(screen.getByLabelText(/business email/i), 'alice@apexfasteners.com');
    await user.type(screen.getByLabelText(/phone number/i), '+15559876543');
    await user.type(screen.getByLabelText(/physical facility/i), '450 Precision Parkway');
    await user.click(screen.getByRole('button', { name: /register supplier/i }));

    await vi.waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });
    const values = handleSubmit.mock.calls[0][0];
    expect(values.companyName).toBe('Apex Fasteners Corp');
    expect(values.email).toBe('alice@apexfasteners.com');
  });
});
