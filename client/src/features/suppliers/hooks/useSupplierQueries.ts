import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query';
import { supplierService } from '../services/supplierService';
import type { SupplierQueryParams } from '../types';
import type { SupplierFormValues } from '../schemas/supplierSchema';

export const SUPPLIER_KEYS = {
  all: ['suppliers'] as const,
  lists: () => [...SUPPLIER_KEYS.all, 'list'] as const,
  list: (params?: SupplierQueryParams) => [...SUPPLIER_KEYS.lists(), params] as const,
  details: () => [...SUPPLIER_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...SUPPLIER_KEYS.details(), id] as const,
};

/**
 * Query hook for paginated, searchable, filtered supplier directory
 */
export function useSuppliers(params?: SupplierQueryParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: SUPPLIER_KEYS.list(params),
    queryFn: () => supplierService.getSuppliers(params),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  });
}

/**
 * Query hook for a single supplier's profile details
 */
export function useSupplierDetail(id?: string) {
  return useQuery({
    queryKey: SUPPLIER_KEYS.detail(id || ''),
    queryFn: () => supplierService.getSupplierById(id || ''),
    enabled: Boolean(id),
    staleTime: 1000 * 60 * 2,
  });
}

/**
 * Mutation hook to register a new supplier
 */
export function useCreateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: SupplierFormValues) => supplierService.createSupplier(values),
    onSuccess: (newSupplier) => {
      queryClient.invalidateQueries({ queryKey: SUPPLIER_KEYS.all });
      queryClient.setQueryData(SUPPLIER_KEYS.detail(newSupplier.id), newSupplier);
    },
  });
}

/**
 * Mutation hook to update a supplier
 */
export function useUpdateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: Partial<SupplierFormValues> }) =>
      supplierService.updateSupplier(id, values),
    onSuccess: (updatedSupplier) => {
      queryClient.invalidateQueries({ queryKey: SUPPLIER_KEYS.all });
      queryClient.setQueryData(SUPPLIER_KEYS.detail(updatedSupplier.id), updatedSupplier);
    },
  });
}

/**
 * Mutation hook to delete a supplier
 */
export function useDeleteSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => supplierService.deleteSupplier(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: SUPPLIER_KEYS.all });
      queryClient.removeQueries({ queryKey: SUPPLIER_KEYS.detail(deletedId) });
    },
  });
}
