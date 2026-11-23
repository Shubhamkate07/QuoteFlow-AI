import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmptyState } from '../EmptyState';

describe('EmptyState Feedback Component', () => {
  it('renders title and description', () => {
    render(
      <EmptyState
        title="No RFQs Found"
        description="Create your first Request for Quotation to begin receiving supplier bids."
      />
    );

    expect(screen.getByText('No RFQs Found')).toBeInTheDocument();
    expect(screen.getByText(/create your first request for quotation/i)).toBeInTheDocument();
  });

  it('renders call to action button and handles clicks', async () => {
    const user = userEvent.setup();
    const handleAction = vi.fn();
    render(
      <EmptyState
        title="No Suppliers Available"
        description="Add a verified vendor."
        actionLabel="Add Supplier"
        onAction={handleAction}
      />
    );

    const button = screen.getByRole('button', { name: /add supplier/i });
    expect(button).toBeInTheDocument();
    await user.click(button);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });
});
