import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateRfqPage } from '../CreateRfqPage';
import * as RfqQueriesModule from '../../../features/rfq/hooks/useRfqQueries';
import { renderWithProviders } from '../../../test/test-utils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../../features/rfq/hooks/useRfqQueries', () => ({
  useCreateRfq: vi.fn(),
}));

describe('CreateRfqPage Integration', () => {
  const mockMutateAsync = vi.fn();
  const mockUseCreateRfq = vi.mocked(RfqQueriesModule.useCreateRfq);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCreateRfq.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    } as any);
  });

  it('renders page header and RFQ creation form', () => {
    renderWithProviders(<CreateRfqPage />);

    expect(screen.getByText('Create Request for Quotation')).toBeInTheDocument();
    expect(screen.getByLabelText(/rfq title/i)).toBeInTheDocument();
  });

  it('creates RFQ and navigates to RFQ detail page upon success', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValueOnce({ id: 'rfq-uuid-101', title: 'Hydraulic Cylinders' });

    renderWithProviders(<CreateRfqPage />);

    await user.type(screen.getByLabelText(/rfq title/i), 'Hydraulic Cylinders');
    await user.click(screen.getByRole('button', { name: /save rfq/i }));

    await vi.waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/rfqs/rfq-uuid-101');
    });
  });

  it('displays server error banner when API creation mutation rejects', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValueOnce({
      response: {
        data: { detail: 'An RFQ with this RFQ Number already exists in your organization.' },
      },
    });

    renderWithProviders(<CreateRfqPage />);

    await user.type(screen.getByLabelText(/rfq title/i), 'Duplicate Cylinders');
    await user.click(screen.getByRole('button', { name: /save rfq/i }));

    expect(
      await screen.findByText('An RFQ with this RFQ Number already exists in your organization.')
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
