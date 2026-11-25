import React, { createContext, useContext, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Supplier } from '../types';
import type { SupplierFormValues } from '../schemas/supplierSchema';
import {
  useSuppliers as useSuppliersQuery,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
  SUPPLIER_KEYS,
} from '../hooks/useSupplierQueries';
import { supplierService } from '../services/supplierService';
import { useAuth } from '../../auth/context/AuthContext';

interface SupplierContextType {
  suppliers: Supplier[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  getSupplierById: (id: string) => Supplier | undefined;
  fetchSupplierById: (id: string) => Promise<Supplier>;
  createSupplier: (values: SupplierFormValues) => Promise<Supplier>;
  updateSupplier: (id: string, values: Partial<SupplierFormValues>) => Promise<Supplier | undefined>;
  deleteSupplier: (id: string) => Promise<boolean>;
}

const SupplierContext = createContext<SupplierContextType | undefined>(undefined);

export const SupplierProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, activeOrganization } = useAuth();
  const queryClient = useQueryClient();

  // Query for workspace-wide supplier list only when authenticated
  const { data, isLoading, isError, refetch } = useSuppliersQuery(undefined, {
    enabled: isAuthenticated,
  });

  const createSupplierMutation = useCreateSupplier();
  const updateSupplierMutation = useUpdateSupplier();
  const deleteSupplierMutation = useDeleteSupplier();

  // Refetch when authenticated or active organization changes, and clear cache on logout
  useEffect(() => {
    if (isAuthenticated) {
      refetch();
    } else {
      queryClient.removeQueries({ queryKey: SUPPLIER_KEYS.all });
    }
  }, [isAuthenticated, activeOrganization?.id, refetch, queryClient]);

  const suppliers = isAuthenticated ? (data?.results || []) : [];

  const getSupplierById = (id: string): Supplier | undefined => {
    return suppliers.find((s) => s.id === id);
  };

  const fetchSupplierById = async (id: string): Promise<Supplier> => {
    return await supplierService.getSupplierById(id);
  };

  const createSupplier = async (values: SupplierFormValues): Promise<Supplier> => {
    return await createSupplierMutation.mutateAsync(values);
  };

  const updateSupplier = async (
    id: string,
    values: Partial<SupplierFormValues>
  ): Promise<Supplier | undefined> => {
    return await updateSupplierMutation.mutateAsync({ id, values });
  };

  const deleteSupplier = async (id: string): Promise<boolean> => {
    await deleteSupplierMutation.mutateAsync(id);
    return true;
  };

  return (
    <SupplierContext.Provider
      value={{
        suppliers,
        isLoading: isAuthenticated ? isLoading : false,
        isError: isAuthenticated ? isError : false,
        refetch,
        getSupplierById,
        fetchSupplierById,
        createSupplier,
        updateSupplier,
        deleteSupplier,
      }}
    >
      {children}
    </SupplierContext.Provider>
  );
};

export const useSuppliers = (): SupplierContextType => {
  const context = useContext(SupplierContext);
  if (!context) {
    throw new Error('useSuppliers must be used within a SupplierProvider');
  }
  return context;
};
