import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  comparisonApi,
  type GenerateComparisonPayload,
  type UpdateWeightsPayload,
} from '../api/comparisonApi';
import type { BackendComparisonResponse } from '../types';

export const COMPARISON_QUERY_KEYS = {
  all: ['comparisons'] as const,
  rfq: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'rfq', rfqId] as const,
  weights: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'weights', rfqId] as const,
  suppliers: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'suppliers', rfqId] as const,
  price: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'price', rfqId] as const,
  specs: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'specs', rfqId] as const,
  risks: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'risks', rfqId] as const,
  scoring: (rfqId: string) => [...COMPARISON_QUERY_KEYS.all, 'scoring', rfqId] as const,
};

/**
 * Hook to retrieve full comprehensive comparison results for an RFQ
 */
export const useRfqComparison = (
  rfqId?: string | null,
  options?: { refresh?: boolean; approvedOnly?: boolean; targetCurrency?: string }
) => {
  return useQuery({
    queryKey: [...COMPARISON_QUERY_KEYS.rfq(rfqId || ''), options],
    queryFn: async () => {
      if (!rfqId) throw new Error('RFQ ID is required');
      return comparisonApi.getRfqComparison(rfqId, options);
    },
    enabled: Boolean(rfqId),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
};

/**
 * Hook to retrieve comparison weights for an RFQ
 */
export const useRfqComparisonWeights = (rfqId?: string | null) => {
  return useQuery({
    queryKey: COMPARISON_QUERY_KEYS.weights(rfqId || ''),
    queryFn: async () => {
      if (!rfqId) throw new Error('RFQ ID is required');
      return comparisonApi.getComparisonWeights(rfqId);
    },
    enabled: Boolean(rfqId),
  });
};

/**
 * Mutation hook to generate a comparison
 */
export const useGenerateComparison = (rfqId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload?: GenerateComparisonPayload) =>
      comparisonApi.generateRfqComparison(rfqId, payload),
    onSuccess: (data: BackendComparisonResponse) => {
      queryClient.setQueryData(COMPARISON_QUERY_KEYS.rfq(rfqId), data);
      queryClient.invalidateQueries({ queryKey: COMPARISON_QUERY_KEYS.rfq(rfqId) });
      queryClient.invalidateQueries({ queryKey: COMPARISON_QUERY_KEYS.weights(rfqId) });
    },
  });
};

/**
 * Mutation hook to force regenerate comparison
 */
export const useRegenerateComparison = (rfqId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => comparisonApi.regenerateRfqComparison(rfqId),
    onSuccess: (data: BackendComparisonResponse) => {
      queryClient.setQueryData(COMPARISON_QUERY_KEYS.rfq(rfqId), data);
      queryClient.invalidateQueries({ queryKey: COMPARISON_QUERY_KEYS.rfq(rfqId) });
    },
  });
};

/**
 * Mutation hook to update customizable scoring weights
 */
export const useUpdateComparisonWeights = (rfqId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateWeightsPayload) =>
      comparisonApi.updateComparisonWeights(rfqId, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: COMPARISON_QUERY_KEYS.weights(rfqId) });
      if (data.comparison) {
        queryClient.setQueryData(COMPARISON_QUERY_KEYS.rfq(rfqId), data.comparison);
      }
      queryClient.invalidateQueries({ queryKey: COMPARISON_QUERY_KEYS.rfq(rfqId) });
    },
  });
};
