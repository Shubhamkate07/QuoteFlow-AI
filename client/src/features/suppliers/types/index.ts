export type SupplierCategory =
  | 'machining'
  | 'sheet_metal'
  | 'fasteners'
  | 'plastics'
  | 'electronics'
  | 'raw_materials'
  | 'surface_treatment'
  | 'other';

export interface Supplier {
  id: string;
  companyName: string;
  contactPerson: string;
  email: string;
  phone: string;
  address: string;
  country?: string;
  gstVatNumber?: string;
  website?: string;
  category: SupplierCategory;
  categoryDisplay?: string;
  notes?: string;
  rating?: number; // 1-5
  status: 'active' | 'pending' | 'inactive';
  statusDisplay?: string;
  activeQuotesCount: number;
  totalQuotesSubmitted: number;
  createdAt: string;
  updatedAt: string;
}

export interface SupplierFilterState {
  searchQuery: string;
  category: string;
  country?: string;
  status: string;
}

/* =========================================================================
   Backend API Types (matching Django REST Framework serializers)
========================================================================= */

export interface BackendSupplier {
  id: string;
  organization_id: string;
  organization_name: string;
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  country: string;
  gst_vat_number: string;
  website: string;
  category: string;
  category_display: string;
  notes: string;
  status: 'active' | 'pending' | 'inactive';
  status_display: string;
  rating: string | number | null;
  created_by_email?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface SupplierQueryParams {
  search?: string;
  category?: string;
  country?: string;
  status?: string;
  page?: number;
}

export interface CreateSupplierPayload {
  company_name: string;
  contact_person: string;
  email: string;
  phone?: string;
  address?: string;
  country?: string;
  gst_vat_number?: string;
  website?: string;
  category: string;
  notes?: string;
  status?: string;
  rating?: number | string | null;
}

export type UpdateSupplierPayload = Partial<CreateSupplierPayload>;

/* =========================================================================
   Data Mappers / Adapters (Backend <-> Frontend)
========================================================================= */

export function adaptBackendSupplier(backend: BackendSupplier): Supplier {
  return {
    id: backend.id,
    companyName: backend.company_name,
    contactPerson: backend.contact_person,
    email: backend.email,
    phone: backend.phone || '',
    address: backend.address || '',
    country: backend.country || 'US',
    gstVatNumber: backend.gst_vat_number || '',
    website: backend.website || '',
    category: (backend.category as SupplierCategory) || 'other',
    categoryDisplay: backend.category_display,
    notes: backend.notes || '',
    rating:
      backend.rating != null && backend.rating !== ''
        ? typeof backend.rating === 'number'
          ? backend.rating
          : parseFloat(String(backend.rating))
        : undefined,
    status: backend.status || 'active',
    statusDisplay: backend.status_display,
    activeQuotesCount: 0,
    totalQuotesSubmitted: 0,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
  };
}
