import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import { extractionService } from '../services/extractionService';
import type {
  SaveCorrectionsPayload,
  ApproveExtractionPayload,
} from '../types/extraction';

export const EXTRACTION_KEYS = {
  all: ['extractions'] as const,
  lists: () => [...EXTRACTION_KEYS.all, 'list'] as const,
  list: (params?: Record<string, any>) => [...EXTRACTION_KEYS.lists(), params] as const,
  details: () => [...EXTRACTION_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...EXTRACTION_KEYS.details(), id] as const,
  auditHistory: (id: string) => [...EXTRACTION_KEYS.all, 'audit-history', id] as const,
  originalData: (id: string) => [...EXTRACTION_KEYS.all, 'original-data', id] as const,
};

/**
 * Query hook to retrieve a specific AI Quotation Extraction by ID.
 * Automatically polls every 2.5 seconds if extraction is still processing.
 */
export function useExtraction(id?: string) {
  return useQuery({
    queryKey: EXTRACTION_KEYS.detail(id || ''),
    queryFn: () => extractionService.getExtractionById(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'processing' || data?.status === 'pending') {
        return 2500;
      }
      return false;
    },
  });
}

/**
 * Query hook to retrieve all extractions for a specific quotation.
 */
export function useExtractionsForQuotation(quotationId?: string) {
  return useQuery({
    queryKey: EXTRACTION_KEYS.list({ quotation: quotationId }),
    queryFn: () => extractionService.getExtractions({ quotation: quotationId }),
    enabled: Boolean(quotationId),
    staleTime: 1000 * 30,
  });
}

/**
 * Mutation hook to trigger AI extraction for a document.
 */
export function useTriggerExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ documentId, sync, model }: { documentId: string; sync?: boolean; model?: string }) =>
      extractionService.triggerExtraction(documentId, sync, model),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.all });
      queryClient.setQueryData(EXTRACTION_KEYS.detail(data.id), data);
    },
  });
}

/**
 * Mutation hook to save human reviewer corrections.
 */
export function useSaveCorrections() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SaveCorrectionsPayload }) =>
      extractionService.saveCorrections(id, payload),
    onSuccess: (res, variables) => {
      queryClient.setQueryData(EXTRACTION_KEYS.detail(variables.id), res.extraction);
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.auditHistory(variables.id) });
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.lists() });
    },
  });
}

/**
 * Mutation hook to mark field paths as reviewed.
 */
export function useMarkFieldsReviewed() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, fields }: { id: string; fields: string[] }) =>
      extractionService.markFieldsReviewed(id, fields),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.detail(variables.id) });
    },
  });
}

/**
 * Mutation hook to approve an extraction.
 */
export function useApproveExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload?: ApproveExtractionPayload }) =>
      extractionService.approveExtraction(id, payload),
    onSuccess: (res, variables) => {
      queryClient.setQueryData(EXTRACTION_KEYS.detail(variables.id), res.extraction);
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.all });
      queryClient.invalidateQueries({ queryKey: ['quotations'] });
    },
  });
}

/**
 * Mutation hook to reject an extraction.
 */
export function useRejectExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      extractionService.rejectExtraction(id, reason),
    onSuccess: (res, variables) => {
      queryClient.setQueryData(EXTRACTION_KEYS.detail(variables.id), res.extraction);
      queryClient.invalidateQueries({ queryKey: EXTRACTION_KEYS.all });
    },
  });
}

/**
 * Query hook to retrieve the audit history of corrections.
 */
export function useExtractionAuditHistory(id?: string) {
  return useQuery({
    queryKey: EXTRACTION_KEYS.auditHistory(id || ''),
    queryFn: () => extractionService.getAuditHistory(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 30,
  });
}

/**
 * Query hook to retrieve pristine original AI extraction data.
 */
export function useOriginalExtractionData(id?: string) {
  return useQuery({
    queryKey: EXTRACTION_KEYS.originalData(id || ''),
    queryFn: () => extractionService.getOriginalData(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 60,
  });
}
