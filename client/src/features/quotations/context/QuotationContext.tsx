import React, { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Quotation, QuotationStatus, UploadQuotationPayload } from '../types';
import type { RfqItem } from '../../rfq/types';
import { useAuth } from '../../auth/context/AuthContext';
import { getErrorMessage } from '../../../lib/api';
import {
  useQuotations as useQuotationsQuery,
  useUploadQuotation,
  useReplaceDocument,
  useDeleteDocument,
  useDeleteQuotation,
  QUOTATION_KEYS,
  invalidateAllQuotationData,
} from '../hooks/useQuotationQueries';

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
  const { isAuthenticated, activeOrganization } = useAuth();
  const queryClient = useQueryClient();

  // Primary server state powered exclusively by React Query
  const {
    data: quotationsData,
    isLoading,
    isError,
    error: queryError,
    refetch,
  } = useQuotationsQuery(undefined, {
    enabled: isAuthenticated,
  });

  const uploadQuotationMutation = useUploadQuotation();
  const replaceDocumentMutation = useReplaceDocument();
  const deleteDocumentMutation = useDeleteDocument();
  const deleteQuotationMutation = useDeleteQuotation();

  // Refetch when authenticated or active org changes, and clear React Query cache on logout
  useEffect(() => {
    if (isAuthenticated) {
      refetch();
    } else {
      queryClient.removeQueries({ queryKey: QUOTATION_KEYS.all });
    }
  }, [isAuthenticated, activeOrganization?.id, refetch, queryClient]);

  const quotations = isAuthenticated && Array.isArray(quotationsData) ? quotationsData : [];
  const error = isError
    ? getErrorMessage(queryError, 'Failed to fetch quotations from backend.')
    : null;

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
    return await uploadQuotationMutation.mutateAsync({ payload, onProgress });
  };

  const replaceDocument = async (
    quotationId: string,
    newFile: File,
    onProgress?: (percent: number) => void
  ): Promise<void> => {
    await replaceDocumentMutation.mutateAsync({ quotationId, newFile, onProgress });
  };

  const deleteDocument = async (documentId: string, quotationId?: string): Promise<void> => {
    await deleteDocumentMutation.mutateAsync({ documentId, quotationId });
  };

  const deleteQuotation = async (quotationId: string): Promise<void> => {
    await deleteQuotationMutation.mutateAsync(quotationId);
  };

  const updateQuotationStatus = (quotationId: string, status: QuotationStatus) => {
    queryClient.setQueriesData<Quotation[]>({ queryKey: QUOTATION_KEYS.all }, (old) => {
      if (!Array.isArray(old)) return old;
      return old.map((q) => (q.id === quotationId ? { ...q, status } : q));
    });
  };

  const updateQuotation = (id: string, updates: Partial<Quotation>) => {
    queryClient.setQueriesData<Quotation[]>({ queryKey: QUOTATION_KEYS.all }, (old) => {
      if (!Array.isArray(old)) return old;
      return old.map((q) => (q.id === id ? { ...q, ...updates } : q));
    });
  };

  const approveQuotation = (id: string) => {
    queryClient.setQueriesData<Quotation[]>({ queryKey: QUOTATION_KEYS.all }, (old) => {
      if (!Array.isArray(old)) return old;
      return old.map((q) =>
        q.id === id
          ? {
              ...q,
              status: 'completed',
              isApproved: true,
              approvedAt: new Date().toISOString(),
              approvedBy: 'Current User',
            }
          : q
      );
    });
    invalidateAllQuotationData(queryClient, id);
  };

  const refreshQuotations = async () => {
    await refetch();
  };

  return (
    <QuotationContext.Provider
      value={{
        quotations,
        isLoading: isAuthenticated ? isLoading : false,
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
        refreshQuotations,
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
