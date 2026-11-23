import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateSupplierPage } from '../CreateSupplierPage';
import * as SupplierQueriesModule from '../../../features/suppliers/hooks/useSupplierQueries';
import { renderWithProviders } from '../../../test/test-utils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../../features/suppliers/hooks/useSupplierQueries', () => ({
  useCreateSupplier: vi.fn(),
}));

describe('CreateSupplierPage Integration', () => {
  const mockMutateAsync = vi.fn();
  const mockUseCreateSupplier = vi.mocked(SupplierQueriesModule.useCreateSupplier);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCreateSupplier.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    } as any);
  });

  it('renders page header and supplier creation form', () => {
    renderWithProviders(<CreateSupplierPage />);

    expect(screen.getByText('Add Approved Supplier')).toBeInTheDocument();
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
  });

  it('submits supplier and navigates to supplier detail page on success', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValueOnce({ id: 'supp-77', companyName: 'Global CNC' });

    renderWithProviders(<CreateSupplierPage />);

    await user.type(screen.getByLabelText(/company name/i), 'Global CNC');
    await user.type(screen.getByLabelText(/primary contact person/i), 'Bob Ross');
    await user.type(screen.getByLabelText(/business email/i), 'bob@globalcnc.com');
    await user.type(screen.getByLabelText(/phone number/i), '+15553334444');
    await user.type(screen.getByLabelText(/physical facility/i), '88 Milling Street');
    await user.click(screen.getByRole('button', { name: /register supplier/i }));

    await vi.waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/suppliers/supp-77');
    });
  });

  it('displays server error banner when creation fails on backend', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValueOnce({
      response: {
        data: { detail: 'A supplier with this company name already exists in your workspace.' },
      },
    });

    renderWithProviders(<CreateSupplierPage />);

    await user.type(screen.getByLabelText(/company name/i), 'Duplicate CNC');
    await user.type(screen.getByLabelText(/primary contact person/i), 'Bob Ross');
    await user.type(screen.getByLabelText(/business email/i), 'bob@globalcnc.com');
    await user.type(screen.getByLabelText(/phone number/i), '+15553334444');
    await user.type(screen.getByLabelText(/physical facility/i), '88 Milling Street');
    await user.click(screen.getByRole('button', { name: /register supplier/i }));

    expect(
      await screen.findByText('A supplier with this company name already exists in your workspace.')
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
