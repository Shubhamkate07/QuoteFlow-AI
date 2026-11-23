import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { Quotation, QuotationStatus, UploadQuotationPayload } from '../types';
import { quotationService } from '../services/quotationService';
import type { RfqItem } from '../../rfq/types';

interface QuotationContextType {
  quotations: Quotation[];
  isLoading: boolean;
  error: string | null;
  getQuotationsByRfq: (rfqId: string) => Quotation[];
  getQuotationById: (id: string) => Quotation | undefined;
  uploadQuotation: (
    payload: UploadQuotationPayload,
    rfqItems?: RfqItem[],
    onProgress?: (percent: number) => void
  ) => Promise<Quotation>;
  replaceDocument: (
    quotationId: string,
    newFile: File,
    onProgress?: (percent: number) => void
  ) => Promise<void>;
  deleteDocument: (documentId: string, quotationId?: string) => Promise<void>;
  deleteQuotation: (quotationId: string) => Promise<void>;
  updateQuotationStatus: (quotationId: string, status: QuotationStatus) => void;
  updateQuotation: (id: string, updates: Partial<Quotation>) => void;
  approveQuotation: (id: string) => void;
  refreshQuotations: () => Promise<void>;
}

const QuotationContext = createContext<QuotationContextType | undefined>(undefined);

export const QuotationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuotations = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await quotationService.getQuotations();
      setQuotations(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch quotations from backend.';
      setError(msg);
      console.warn('Error fetching quotations:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuotations();
  }, [fetchQuotations]);

  const getQuotationsByRfq = (rfqId: string): Quotation[] => {
    return quotations.filter((q) => q.rfqId === rfqId);
  };

  const getQuotationById = (id: string): Quotation | undefined => {
    return quotations.find((q) => q.id === id);
  };

  const uploadQuotation = async (
    payload: UploadQuotationPayload,
    _rfqItems?: RfqItem[],
    onProgress?: (percent: number) => void
  ): Promise<Quotation> => {
    const createdQuote = await quotationService.uploadQuotationWithDocument(payload, onProgress);
    setQuotations((prev) => [createdQuote, ...prev.filter((q) => q.id !== createdQuote.id)]);
    return createdQuote;
  };

  const replaceDocument = async (
    quotationId: string,
    newFile: File,
    onProgress?: (percent: number) => void
  ): Promise<void> => {
    await quotationService.attachDocument(quotationId, newFile, onProgress);
    const updated = await quotationService.getQuotationById(quotationId);
    setQuotations((prev) => prev.map((q) => (q.id === quotationId ? updated : q)));
  };

  const deleteDocument = async (documentId: string, quotationId?: string): Promise<void> => {
    await quotationService.deleteDocument(documentId);
    if (quotationId) {
      const updated = await quotationService.getQuotationById(quotationId);
      setQuotations((prev) => prev.map((q) => (q.id === quotationId ? updated : q)));
    } else {
      await fetchQuotations();
    }
  };

  const deleteQuotation = async (quotationId: string): Promise<void> => {
    await quotationService.deleteQuotation(quotationId);
    setQuotations((prev) => prev.filter((q) => q.id !== quotationId));
  };

  const updateQuotationStatus = (quotationId: string, status: QuotationStatus) => {
    setQuotations((prev) =>
      prev.map((q) => (q.id === quotationId ? { ...q, status } : q))
    );
  };

  const updateQuotation = (id: string, updates: Partial<Quotation>) => {
    setQuotations((prev) =>
      prev.map((q) => {
        if (q.id !== id) return q;
        return { ...q, ...updates };
      })
    );
  };

  const approveQuotation = (id: string) => {
    setQuotations((prev) =>
      prev.map((q) =>
        q.id === id
          ? {
              ...q,
              status: 'completed',
              isApproved: true,
              approvedAt: new Date().toISOString(),
              approvedBy: 'Current User',
            }
          : q
      )
    );
  };

  return (
    <QuotationContext.Provider
      value={{
        quotations,
        isLoading,
        error,
        getQuotationsByRfq,
        getQuotationById,
        uploadQuotation,
        replaceDocument,
        deleteDocument,
        deleteQuotation,
        updateQuotationStatus,
        updateQuotation,
        approveQuotation,
        refreshQuotations: fetchQuotations,
      }}
    >
      {children}
    </QuotationContext.Provider>
  );
};

export const useQuotation = (): QuotationContextType => {
  const context = useContext(QuotationContext);
  if (!context) {
    throw new Error('useQuotation must be used within a QuotationProvider');
  }
  return context;
};
