import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RfqListPage } from '../RfqListPage';
import * as RfqQueriesModule from '../../../features/rfq/hooks/useRfqQueries';
import { renderWithProviders } from '../../../test/test-utils';

vi.mock('../../../features/rfq/hooks/useRfqQueries', () => ({
  useRfqs: vi.fn(),
  useDeleteRfq: vi.fn(),
}));

describe('RfqListPage UI, Loading, Error, and Filter States', () => {
  const mockUseRfqs = vi.mocked(RfqQueriesModule.useRfqs);
  const mockUseDeleteRfq = vi.mocked(RfqQueriesModule.useDeleteRfq);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDeleteRfq.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
  });

  it('renders loading spinner while RFQs are being fetched', () => {
    mockUseRfqs.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RfqListPage />);

    expect(screen.getByText('Loading RFQs from server...')).toBeInTheDocument();
  });

  it('renders error state with retry button when query fails', async () => {
    const user = userEvent.setup();
    const mockRefetch = vi.fn();
    mockUseRfqs.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      isError: true,
      error: new Error('Failed to load RFQs from server'),
      refetch: mockRefetch,
    } as any);

    renderWithProviders(<RfqListPage />);

    expect(screen.getByText('Failed to load RFQs')).toBeInTheDocument();
    expect(screen.getByText('Failed to load RFQs from server')).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    await user.click(retryBtn);
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('renders empty state when zero RFQs exist', () => {
    mockUseRfqs.mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RfqListPage />);

    expect(screen.getByText('No RFQs created yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create first rfq/i })).toBeInTheDocument();
  });

  it('renders table rows when RFQs are returned from API', () => {
    const mockResults = [
      {
        id: 'rfq-1',
        rfqNumber: 'RFQ-2026-0001',
        title: 'Precision Machined Brackets',
        status: 'open',
        currency: 'USD',
        targetBudget: 15000,
        createdAt: '2026-11-20T10:00:00Z',
        requiredDeliveryDate: '2026-12-15',
        itemCount: 4,
        quotationCount: 2,
        invitedSupplierIds: [],
        items: [],
      },
    ];

    mockUseRfqs.mockReturnValue({
      data: { results: mockResults, count: 1 },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RfqListPage />);

    expect(screen.getByText('RFQ-2026-0001')).toBeInTheDocument();
    expect(screen.getByText('Precision Machined Brackets')).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: /open for bids/i })).toBeInTheDocument();
  });
});
