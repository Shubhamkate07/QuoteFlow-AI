import api from '../../../lib/api';
import type { PaginatedResponse } from '../../../types/api';
import type {
  Supplier,
  BackendSupplier,
  SupplierQueryParams,
  CreateSupplierPayload,
  UpdateSupplierPayload,
} from '../types';
import { adaptBackendSupplier } from '../types';
import type { SupplierFormValues } from '../schemas/supplierSchema';

export const supplierService = {
  /**
   * Fetches paginated list of suppliers with search, category, and status filters
   */
  getSuppliers: async (params?: SupplierQueryParams): Promise<PaginatedResponse<Supplier>> => {
    const cleanParams: Record<string, any> = {};
    if (params?.search?.trim()) cleanParams.search = params.search.trim();
    if (params?.category && params.category !== 'all') cleanParams.category = params.category;
    if (params?.country && params.country !== 'all') cleanParams.country = params.country;
    if (params?.status && params.status !== 'all') cleanParams.status = params.status;
    if (params?.page) cleanParams.page = params.page;

    const response = await api.get<PaginatedResponse<BackendSupplier>>('/suppliers/', {
      params: cleanParams,
    });

    return {
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
      results: (response.data.results || []).map((item) => adaptBackendSupplier(item)),
    };
  },

  /**
   * Retrieves full profile for a single supplier
   */
  getSupplierById: async (id: string): Promise<Supplier> => {
    const response = await api.get<BackendSupplier>(`/suppliers/${id}/`);
    return adaptBackendSupplier(response.data);
  },

  /**
   * Registers a new supplier in the workspace directory
   */
  createSupplier: async (values: SupplierFormValues): Promise<Supplier> => {
    const payload: CreateSupplierPayload = {
      company_name: values.companyName.trim(),
      contact_person: values.contactPerson.trim(),
      email: values.email.trim().toLowerCase(),
      phone: values.phone?.trim() || '',
      address: values.address?.trim() || '',
      country: values.country?.trim() || 'US',
      gst_vat_number: values.gstVatNumber?.trim() || '',
      website: values.website?.trim() || '',
      category: values.category,
      notes: values.notes?.trim() || '',
      status: values.status,
    };

    const response = await api.post<BackendSupplier>('/suppliers/', payload);
    return adaptBackendSupplier(response.data);
  },

  /**
   * Updates an existing supplier record
   */
  updateSupplier: async (id: string, values: Partial<SupplierFormValues>): Promise<Supplier> => {
    const payload: UpdateSupplierPayload = {};

    if (values.companyName !== undefined) payload.company_name = values.companyName.trim();
    if (values.contactPerson !== undefined) payload.contact_person = values.contactPerson.trim();
    if (values.email !== undefined) payload.email = values.email.trim().toLowerCase();
    if (values.phone !== undefined) payload.phone = values.phone.trim();
    if (values.address !== undefined) payload.address = values.address.trim();
    if (values.country !== undefined) payload.country = values.country.trim();
    if (values.gstVatNumber !== undefined) payload.gst_vat_number = values.gstVatNumber.trim();
    if (values.website !== undefined) payload.website = values.website.trim();
    if (values.category !== undefined) payload.category = values.category;
    if (values.notes !== undefined) payload.notes = values.notes.trim();
    if (values.status !== undefined) payload.status = values.status;

    const response = await api.patch<BackendSupplier>(`/suppliers/${id}/`, payload);
    return adaptBackendSupplier(response.data);
  },

  /**
   * Deletes a supplier from the directory
   */
  deleteSupplier: async (id: string): Promise<void> => {
    await api.delete(`/suppliers/${id}/`);
  },
};
