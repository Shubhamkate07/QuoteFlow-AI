import React, { createContext, useContext } from 'react';
import type { Supplier } from '../types';
import type { SupplierFormValues } from '../schemas/supplierSchema';
import {
  useSuppliers as useSuppliersQuery,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
} from '../hooks/useSupplierQueries';
import { supplierService } from '../services/supplierService';

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
  // Query for workspace-wide supplier list
  const { data, isLoading, isError, refetch } = useSuppliersQuery();

  const createSupplierMutation = useCreateSupplier();
  const updateSupplierMutation = useUpdateSupplier();
  const deleteSupplierMutation = useDeleteSupplier();

  const suppliers = data?.results || [];

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
        isLoading,
        isError,
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
