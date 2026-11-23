import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal } from '../Modal';

describe('Modal UI Component', () => {
  it('does not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={vi.fn()} title="Hidden Modal">
        <p>Modal content</p>
      </Modal>
    );
    expect(screen.queryByText('Hidden Modal')).not.toBeInTheDocument();
    expect(screen.queryByText('Modal content')).not.toBeInTheDocument();
  });

  it('renders title, description, content and footer when isOpen is true', () => {
    render(
      <Modal
        isOpen={true}
        onClose={vi.fn()}
        title="Confirm Deletion"
        description="This action cannot be undone."
        footer={<button>Confirm</button>}
      >
        <p>Are you sure you want to delete this supplier?</p>
      </Modal>
    );

    expect(screen.getByText('Confirm Deletion')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this supplier?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
  });

  it('calls onClose when close icon button is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Test Modal">
        Body
      </Modal>
    );

    const closeButton = screen.getByRole('button', { name: /close dialog/i });
    await user.click(closeButton);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Escape Test">
        Body
      </Modal>
    );

    await user.keyboard('{Escape}');
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
