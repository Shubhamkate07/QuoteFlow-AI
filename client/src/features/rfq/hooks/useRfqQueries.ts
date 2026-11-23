import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query';
import { rfqService } from '../services/rfqService';
import type { RfqQueryParams } from '../types';
import type { RfqFormValues, RfqItemFormValues } from '../schemas/rfqSchema';

export const RFQ_KEYS = {
  all: ['rfqs'] as const,
  lists: () => [...RFQ_KEYS.all, 'list'] as const,
  list: (params?: RfqQueryParams) => [...RFQ_KEYS.lists(), params] as const,
  details: () => [...RFQ_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...RFQ_KEYS.details(), id] as const,
};

/**
 * Query hook for paginated, searchable, filtered RFQ list
 */
export function useRfqs(params?: RfqQueryParams) {
  return useQuery({
    queryKey: RFQ_KEYS.list(params),
    queryFn: () => rfqService.getRfqs(params),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

/**
 * Query hook for a single RFQ's details and items
 */
export function useRfqDetail(id?: string) {
  return useQuery({
    queryKey: RFQ_KEYS.detail(id || ''),
    queryFn: () => rfqService.getRfqById(id || ''),
    enabled: Boolean(id),
    staleTime: 1000 * 60 * 2,
  });
}

/**
 * Mutation hook to create an RFQ
 */
export function useCreateRfq() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: RfqFormValues) => rfqService.createRfq(values),
    onSuccess: (newRfq) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.all });
      queryClient.setQueryData(RFQ_KEYS.detail(newRfq.id), newRfq);
    },
  });
}

/**
 * Mutation hook to update an RFQ
 */
export function useUpdateRfq() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: Partial<RfqFormValues> }) =>
      rfqService.updateRfq(id, values),
    onSuccess: (updatedRfq) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.all });
      queryClient.setQueryData(RFQ_KEYS.detail(updatedRfq.id), updatedRfq);
    },
  });
}

/**
 * Mutation hook to delete an RFQ
 */
export function useDeleteRfq() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => rfqService.deleteRfq(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.all });
      queryClient.removeQueries({ queryKey: RFQ_KEYS.detail(deletedId) });
    },
  });
}

/**
 * Mutation hook to add an item to an RFQ
 */
export function useAddRfqItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ rfqId, values }: { rfqId: string; values: RfqItemFormValues }) =>
      rfqService.addRfqItem(rfqId, values),
    onSuccess: (_, { rfqId }) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.detail(rfqId) });
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.lists() });
    },
  });
}

/**
 * Mutation hook to update a line item on an RFQ
 */
export function useUpdateRfqItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      rfqId,
      itemId,
      values,
    }: {
      rfqId: string;
      itemId: string;
      values: Partial<RfqItemFormValues>;
    }) => rfqService.updateRfqItem(rfqId, itemId, values),
    onSuccess: (_, { rfqId }) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.detail(rfqId) });
    },
  });
}

/**
 * Mutation hook to delete a line item from an RFQ
 */
export function useDeleteRfqItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ rfqId, itemId }: { rfqId: string; itemId: string }) =>
      rfqService.deleteRfqItem(rfqId, itemId),
    onSuccess: (_, { rfqId }) => {
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.detail(rfqId) });
      queryClient.invalidateQueries({ queryKey: RFQ_KEYS.lists() });
    },
  });
}
