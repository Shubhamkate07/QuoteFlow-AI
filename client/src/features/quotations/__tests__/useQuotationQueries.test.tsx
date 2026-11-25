import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';
import {
  useDeleteQuotation,
  QUOTATION_KEYS,
  invalidateAllQuotationData,
} from '../hooks/useQuotationQueries';
import { quotationService } from '../services/quotationService';
import type { Quotation } from '../types';

vi.mock('../services/quotationService', () => ({
  quotationService: {
    getQuotations: vi.fn(),
    getQuotationsByRfq: vi.fn(),
    getQuotationById: vi.fn(),
    deleteQuotation: vi.fn(),
    deleteDocument: vi.fn(),
    attachDocument: vi.fn(),
    uploadQuotationWithDocument: vi.fn(),
  },
}));

describe('useQuotationQueries React Query Single Source of Truth', () => {
  let queryClient: QueryClient;

  const mockQuotes: Quotation[] = [
    {
      id: 'quote-1',
      rfqId: 'rfq-101',
      rfqNumber: 'RFQ-101',
      supplierId: 'sup-1',
      supplierName: 'Alpha Supplies',
      quoteReference: 'QT-001',
      uploadedAt: '2026-11-20',
      fileName: 'alpha_bid.pdf',
      fileSize: '1.2 MB',
      fileType: 'pdf',
      status: 'completed',
      processingProgress: 100,
      totalAmount: 5000,
      subtotal: 4500,
      currency: 'USD',
      commercialTerms: {
        paymentTerms: 'Net 30',
        deliveryLeadWeeks: 2,
        incoterms: 'DDP',
        validUntil: '2026-12-31',
        warrantyTerms: '1 Year',
        taxesApplicable: 'Excluded',
      },
      extractedItems: [],
    },
    {
      id: 'quote-2',
      rfqId: 'rfq-101',
      rfqNumber: 'RFQ-101',
      supplierId: 'sup-2',
      supplierName: 'Beta Tools',
      quoteReference: 'QT-002',
      uploadedAt: '2026-11-21',
      fileName: 'beta_bid.xlsx',
      fileSize: '850 KB',
      fileType: 'excel',
      status: 'completed',
      processingProgress: 100,
      totalAmount: 7200,
      subtotal: 6800,
      currency: 'USD',
      commercialTerms: {
        paymentTerms: 'Net 60',
        deliveryLeadWeeks: 4,
        incoterms: 'FOB',
        validUntil: '2026-12-31',
        warrantyTerms: '2 Years',
        taxesApplicable: 'Excluded',
      },
      extractedItems: [],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  it('optimistically removes deleted quotation from cache on mutation', async () => {
    // Populate query cache with initial quotations
    queryClient.setQueryData(QUOTATION_KEYS.list(), mockQuotes);
    queryClient.setQueryData(QUOTATION_KEYS.byRfq('rfq-101'), mockQuotes);

    vi.mocked(quotationService.deleteQuotation).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 50))
    );

    const { result } = renderHook(() => useDeleteQuotation(), {
      wrapper: createWrapper(),
    });

    // Trigger delete mutation
    result.current.mutate('quote-1');

    // Immediately verify optimistic removal from cache
    await waitFor(() => {
      const cached = queryClient.getQueryData<Quotation[]>(QUOTATION_KEYS.list());
      expect(cached).toHaveLength(1);
      expect(cached?.[0].id).toBe('quote-2');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rolls back cache to previous state when deletion fails', async () => {
    queryClient.setQueryData(QUOTATION_KEYS.list(), mockQuotes);

    // Mock failure
    vi.mocked(quotationService.deleteQuotation).mockRejectedValueOnce(
      new Error('Network error deleting quotation')
    );

    const { result } = renderHook(() => useDeleteQuotation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('quote-1');

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Verify cache was rolled back to original 2 items
    const rolledBack = queryClient.getQueryData<Quotation[]>(QUOTATION_KEYS.list());
    expect(rolledBack).toHaveLength(2);
    expect(rolledBack?.map((q) => q.id)).toEqual(['quote-1', 'quote-2']);
  });

  it('invalidates all quotation-dependent queries upon delete completion', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    invalidateAllQuotationData(queryClient, 'quote-1', 'rfq-101');

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QUOTATION_KEYS.all });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['extractions'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['comparisons'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rfqs'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['dashboard'] });
  });
});
