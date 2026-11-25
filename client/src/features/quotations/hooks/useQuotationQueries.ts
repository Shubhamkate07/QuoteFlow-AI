import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
  type QueryClient,
} from '@tanstack/react-query';
import { quotationService } from '../services/quotationService';
import type {
  Quotation,
  UploadQuotationPayload,
} from '../types';

export const QUOTATION_KEYS = {
  all: ['quotations'] as const,
  lists: () => [...QUOTATION_KEYS.all, 'list'] as const,
  list: (params?: Record<string, any>) => [...QUOTATION_KEYS.lists(), params] as const,
  byRfq: (rfqId?: string) => [...QUOTATION_KEYS.all, 'by-rfq', rfqId] as const,
  details: () => [...QUOTATION_KEYS.all, 'detail'] as const,
  detail: (id?: string) => [...QUOTATION_KEYS.details(), id] as const,
};

/**
 * Centrally invalidates all quotation-dependent queries across the entire workspace:
 * quotations list, by-rfq, details, AI extractions, multi-bid comparisons, RFQ packages, and dashboard metrics.
 */
export function invalidateAllQuotationData(
  queryClient: QueryClient,
  quotationId?: string,
  rfqId?: string
) {
  queryClient.invalidateQueries({ queryKey: QUOTATION_KEYS.all });
  queryClient.invalidateQueries({ queryKey: ['extractions'] });
  queryClient.invalidateQueries({ queryKey: ['comparisons'] });
  queryClient.invalidateQueries({ queryKey: ['rfqs'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard'] });

  if (quotationId) {
    queryClient.removeQueries({ queryKey: QUOTATION_KEYS.detail(quotationId) });
  }
  if (rfqId) {
    queryClient.invalidateQueries({ queryKey: QUOTATION_KEYS.byRfq(rfqId) });
  }
}

/**
 * Query hook for all quotations with optional filters (e.g. search, rfq, supplier).
 */
export function useQuotations(
  params?: { rfq?: string; supplier?: string; search?: string },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: QUOTATION_KEYS.list(params),
    queryFn: () => quotationService.getQuotations(params),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 30, // 30 seconds
    enabled: options?.enabled ?? true,
  });
}

/**
 * Query hook for quotations associated with a specific RFQ.
 */
export function useQuotationsByRfq(
  rfqId?: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: QUOTATION_KEYS.byRfq(rfqId),
    queryFn: () => (rfqId ? quotationService.getQuotationsByRfq(rfqId) : Promise.resolve([])),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 30,
    enabled: Boolean(rfqId) && (options?.enabled ?? true),
  });
}

/**
 * Query hook for retrieving a single quotation by ID.
 */
export function useQuotationDetail(
  id?: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: QUOTATION_KEYS.detail(id),
    queryFn: () => (id ? quotationService.getQuotationById(id) : Promise.reject('No ID provided')),
    staleTime: 1000 * 30,
    enabled: Boolean(id) && (options?.enabled ?? true),
  });
}

/**
 * Mutation hook to upload a quotation document and create a new quotation.
 */
export function useUploadQuotation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      payload,
      onProgress,
    }: {
      payload: UploadQuotationPayload;
      onProgress?: (percent: number) => void;
    }) => quotationService.uploadQuotationWithDocument(payload, onProgress),
    onSuccess: (newQuotation) => {
      invalidateAllQuotationData(queryClient, newQuotation.id, newQuotation.rfqId);
    },
  });
}

/**
 * Mutation hook to attach/replace a document on an existing quotation.
 */
export function useReplaceDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      quotationId,
      newFile,
      onProgress,
    }: {
      quotationId: string;
      newFile: File;
      onProgress?: (percent: number) => void;
    }) => quotationService.attachDocument(quotationId, newFile, onProgress),
    onSuccess: (_, { quotationId }) => {
      invalidateAllQuotationData(queryClient, quotationId);
    },
  });
}

/**
 * Mutation hook to delete a specific document attached to a quotation.
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
    }: {
      documentId: string;
      quotationId?: string;
    }) => quotationService.deleteDocument(documentId),
    onSuccess: (_, { quotationId }) => {
      invalidateAllQuotationData(queryClient, quotationId);
    },
  });
}

/**
 * Mutation hook to delete a quotation with optimistic removal and rollback on error.
 */
export function useDeleteQuotation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (quotationId: string) => quotationService.deleteQuotation(quotationId),
    onMutate: async (deletedId: string) => {
      // Cancel outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: QUOTATION_KEYS.all });

      // Snapshot previous query data for all quotation keys
      const previousQueries = queryClient.getQueriesData({ queryKey: QUOTATION_KEYS.all });

      // Optimistically remove deleted quotation from cache across all quotation queries
      queryClient.setQueriesData<Quotation[] | { results?: Quotation[] }>(
        { queryKey: QUOTATION_KEYS.all },
        (oldData) => {
          if (!oldData) return oldData;
          if (Array.isArray(oldData)) {
            return oldData.filter((q) => q && q.id !== deletedId);
          }
          if ('results' in oldData && Array.isArray(oldData.results)) {
            return {
              ...oldData,
              results: oldData.results.filter((q) => q && q.id !== deletedId),
            };
          }
          return oldData;
        }
      );

      return { previousQueries };
    },
    onError: (_err, _deletedId, context) => {
      // Roll back to previous snapshot if delete fails
      if (context?.previousQueries) {
        context.previousQueries.forEach(([key, data]) => {
          queryClient.setQueryData(key, data);
        });
      }
    },
    onSettled: (_data, _error, deletedId) => {
      // Always invalidate to ensure cache is in sync with server state
      invalidateAllQuotationData(queryClient, deletedId);
    },
  });
}
