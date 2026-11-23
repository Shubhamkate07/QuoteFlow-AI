import React, { createContext, useContext } from 'react';
import type { Rfq, RfqItem } from '../types';
import type { RfqFormValues, RfqItemFormValues } from '../schemas/rfqSchema';
import {
  useRfqs,
  useCreateRfq,
  useUpdateRfq,
  useDeleteRfq,
  useAddRfqItem,
  useUpdateRfqItem,
  useDeleteRfqItem,
} from '../hooks/useRfqQueries';
import { rfqService } from '../services/rfqService';

interface RfqContextType {
  rfqs: Rfq[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  getRfqById: (id: string) => Rfq | undefined;
  fetchRfqById: (id: string) => Promise<Rfq>;
  createRfq: (values: RfqFormValues) => Promise<Rfq>;
  updateRfq: (id: string, values: Partial<RfqFormValues>) => Promise<Rfq | undefined>;
  deleteRfq: (id: string) => Promise<boolean>;
  addRfqItem: (rfqId: string, itemValues: RfqItemFormValues) => Promise<RfqItem | undefined>;
  updateRfqItem: (rfqId: string, itemId: string, itemValues: Partial<RfqItemFormValues>) => Promise<void>;
  deleteRfqItem: (rfqId: string, itemId: string) => Promise<void>;
}

const RfqContext = createContext<RfqContextType | undefined>(undefined);

export const RfqProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Fetch initial list of RFQs for workspace subscribers
  const { data, isLoading, isError, refetch } = useRfqs();

  const createRfqMutation = useCreateRfq();
  const updateRfqMutation = useUpdateRfq();
  const deleteRfqMutation = useDeleteRfq();
  const addRfqItemMutation = useAddRfqItem();
  const updateRfqItemMutation = useUpdateRfqItem();
  const deleteRfqItemMutation = useDeleteRfqItem();

  const rfqs = data?.results || [];

  const getRfqById = (id: string): Rfq | undefined => {
    return rfqs.find((r) => r.id === id || r.rfqNumber === id);
  };

  const fetchRfqById = async (id: string): Promise<Rfq> => {
    return await rfqService.getRfqById(id);
  };

  const createRfq = async (values: RfqFormValues): Promise<Rfq> => {
    return await createRfqMutation.mutateAsync(values);
  };

  const updateRfq = async (id: string, values: Partial<RfqFormValues>): Promise<Rfq | undefined> => {
    return await updateRfqMutation.mutateAsync({ id, values });
  };

  const deleteRfq = async (id: string): Promise<boolean> => {
    await deleteRfqMutation.mutateAsync(id);
    return true;
  };

  const addRfqItem = async (rfqId: string, itemValues: RfqItemFormValues): Promise<RfqItem | undefined> => {
    return await addRfqItemMutation.mutateAsync({ rfqId, values: itemValues });
  };

  const updateRfqItem = async (
    rfqId: string,
    itemId: string,
    itemValues: Partial<RfqItemFormValues>
  ): Promise<void> => {
    await updateRfqItemMutation.mutateAsync({ rfqId, itemId, values: itemValues });
  };

  const deleteRfqItem = async (rfqId: string, itemId: string): Promise<void> => {
    await deleteRfqItemMutation.mutateAsync({ rfqId, itemId });
  };

  return (
    <RfqContext.Provider
      value={{
        rfqs,
        isLoading,
        isError,
        refetch,
        getRfqById,
        fetchRfqById,
        createRfq,
        updateRfq,
        deleteRfq,
        addRfqItem,
        updateRfqItem,
        deleteRfqItem,
      }}
    >
      {children}
    </RfqContext.Provider>
  );
};

export const useRfq = (): RfqContextType => {
  const context = useContext(RfqContext);
  if (!context) {
    throw new Error('useRfq must be used within an RfqProvider');
  }
  return context;
};
