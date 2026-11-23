import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuotationUploadModal } from '../components/QuotationUploadModal';
import * as SupplierContextModule from '../../suppliers/context/SupplierContext';
import * as QuotationContextModule from '../context/QuotationContext';
import { renderWithProviders } from '../../../test/test-utils';

vi.mock('../../suppliers/context/SupplierContext', () => ({
  useSuppliers: vi.fn(),
}));

vi.mock('../context/QuotationContext', () => ({
  useQuotation: vi.fn(),
}));

describe('QuotationUploadModal UI and File Validation', () => {
  const mockUploadQuotation = vi.fn();
  const mockUseSuppliers = vi.mocked(SupplierContextModule.useSuppliers);
  const mockUseQuotation = vi.mocked(QuotationContextModule.useQuotation);

  const mockSuppliers = [
    {
      id: 'supp-1',
      companyName: 'Apex Precision Ltd',
      contactPerson: 'David Miller',
      email: 'quotes@apex.com',
      phone: '+1555123456',
      address: '100 Industrial Road',
      country: 'US',
      category: 'machining' as const,
      status: 'active' as const,
      quotationCount: 2,
      createdAt: '2026-11-20',
      updatedAt: '2026-11-20',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuppliers.mockReturnValue({
      suppliers: mockSuppliers,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    mockUseQuotation.mockReturnValue({
      uploadQuotation: mockUploadQuotation,
      isUploading: false,
    } as any);
  });

  it('renders modal dialog when isOpen is true', () => {
    renderWithProviders(
      <QuotationUploadModal
        isOpen={true}
        onClose={vi.fn()}
        rfqId="rfq-1"
        rfqCurrency="USD"
        rfqItems={[]}
      />
    );

    expect(screen.getByText('Upload Supplier Quotation')).toBeInTheDocument();
    expect(screen.getByLabelText(/bidding supplier/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/quote reference \/ id/i)).toBeInTheDocument();
  });

  it('rejects unsupported file extension (.exe) with error message', async () => {
    renderWithProviders(
      <QuotationUploadModal
        isOpen={true}
        onClose={vi.fn()}
        rfqId="rfq-1"
        rfqCurrency="USD"
        rfqItems={[]}
      />
    );

    const badFile = new File(['executable binary content'], 'quotation.exe', {
      type: 'application/x-msdownload',
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();
    fireEvent.change(fileInput, { target: { files: [badFile] } });

    expect(
      await screen.findByText(/unsupported file format \(\.exe\)/i)
    ).toBeInTheDocument();
    expect(mockUploadQuotation).not.toHaveBeenCalled();
  });

  it('accepts valid PDF file and auto-populates reference', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <QuotationUploadModal
        isOpen={true}
        onClose={vi.fn()}
        rfqId="rfq-1"
        rfqCurrency="USD"
        rfqItems={[]}
      />
    );

    const validPdf = new File(['%PDF-1.4 mock content'], 'Apex_Valves_Q100.pdf', {
      type: 'application/pdf',
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, validPdf);

    expect(screen.getByText('Apex_Valves_Q100.pdf')).toBeInTheDocument();
    expect(screen.queryByText(/unsupported file format/i)).not.toBeInTheDocument();
  });
});
