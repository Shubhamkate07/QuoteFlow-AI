export type RfqStatus = 'draft' | 'open' | 'under_review' | 'awarded' | 'closed';

export interface ItemSpecificationAttr {
  key: string;
  value: string;
}

export interface RfqItem {
  id: string;
  itemNumber: string;
  name: string;
  description?: string;
  quantity: number;
  unit: string;
  targetUnitPrice?: number;
  requiredSpecifications: string;
  specsList?: ItemSpecificationAttr[];
  manufacturerPreference?: string;
  modelPreference?: string;
  requiredDeliveryDate?: string;
  notes?: string;
}

export interface RfqSupplierQuoteSummary {
  id: string;
  supplierName: string;
  quoteReference: string;
  totalAmount: number;
  currency: string;
  deliveryLeadWeeks: number;
  submittedAt: string;
  specMatchPercentage: number;
}

export interface Rfq {
  id: string;
  rfqNumber: string;
  title: string;
  description: string;
  requiredDeliveryDate: string;
  currency: 'USD' | 'EUR' | 'GBP' | 'CAD' | 'JPY' | string;
  status: RfqStatus;
  statusDisplay?: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
  targetBudget: number;
  itemsCount?: number;
  items: RfqItem[];
  quotes: RfqSupplierQuoteSummary[];
}

export interface RfqFilterState {
  searchQuery: string;
  status: string;
  dateRange: string;
  currency: string;
}

/* =========================================================================
   Backend API Types (matching Django REST Framework serializers)
========================================================================= */

export interface BackendSpecification {
  id?: string;
  parameter_name: string;
  required_value: string;
  tolerance_or_unit?: string;
  importance?: 'mandatory' | 'preferred' | 'optional';
  notes?: string;
}

export interface BackendRfqItem {
  id: string;
  rfq_id?: string;
  position: number;
  item_name: string;
  description?: string;
  quantity: string | number;
  unit: string;
  target_unit_price?: string | number | null;
  manufacturer_preference?: string;
  model_preference?: string;
  required_delivery_date?: string | null;
  effective_delivery_date?: string | null;
  custom_specifications?: Record<string, any>;
  notes?: string;
  specifications: BackendSpecification[];
  created_at?: string;
  updated_at?: string;
}

export interface BackendRfqListItem {
  id: string;
  rfq_number: string;
  title: string;
  description: string;
  status: RfqStatus;
  status_display: string;
  currency: string;
  required_delivery_date: string | null;
  items_count: number;
  created_by_email: string;
  created_at: string;
  updated_at: string;
}

export interface BackendRfqDetail extends BackendRfqListItem {
  organization_id: string;
  organization_name: string;
  notes: string;
  items: BackendRfqItem[];
  created_by_name: string;
}

export interface RfqQueryParams {
  search?: string;
  status?: string;
  currency?: string;
  page?: number;
}

export interface CreateRfqPayload {
  title: string;
  rfq_number?: string;
  description?: string;
  status?: RfqStatus;
  required_delivery_date?: string | null;
  currency?: string;
  notes?: string;
  items?: CreateRfqItemPayload[];
}

export interface UpdateRfqPayload {
  title?: string;
  rfq_number?: string;
  description?: string;
  status?: RfqStatus;
  required_delivery_date?: string | null;
  currency?: string;
  notes?: string;
}

export interface CreateRfqItemPayload {
  item_name: string;
  quantity: number | string;
  unit?: string;
  position?: number;
  description?: string;
  target_unit_price?: number | string | null;
  manufacturer_preference?: string;
  model_preference?: string;
  required_delivery_date?: string | null;
  custom_specifications?: Record<string, any>;
  notes?: string;
  specifications?: Array<{
    parameter_name: string;
    required_value: string;
    tolerance_or_unit?: string;
    importance?: 'mandatory' | 'preferred' | 'optional';
    notes?: string;
  }>;
}

export type UpdateRfqItemPayload = Partial<CreateRfqItemPayload>;

/* =========================================================================
   Data Mappers / Adapters (Backend <-> Frontend)
========================================================================= */

export function adaptBackendRfqItem(backendItem: BackendRfqItem, index?: number): RfqItem {
  const specs = backendItem.specifications || [];
  const specsList = specs.map((s) => ({
    key: s.parameter_name,
    value: s.tolerance_or_unit ? `${s.required_value} ${s.tolerance_or_unit}` : s.required_value,
  }));

  const requiredSpecifications =
    backendItem.custom_specifications?.required_spec_summary ||
    (specs.length > 0 ? specs.map((s) => `${s.parameter_name}: ${s.required_value}`).join('; ') : '') ||
    backendItem.description ||
    '';

  const position = backendItem.position ?? (index !== undefined ? index + 1 : 1);

  return {
    id: backendItem.id,
    itemNumber: `#${String(position).padStart(2, '0')}`,
    name: backendItem.item_name,
    description: backendItem.description || '',
    quantity: typeof backendItem.quantity === 'number' ? backendItem.quantity : parseFloat(String(backendItem.quantity)) || 0,
    unit: backendItem.unit || 'PCS',
    targetUnitPrice:
      backendItem.target_unit_price != null && backendItem.target_unit_price !== ''
        ? typeof backendItem.target_unit_price === 'number'
          ? backendItem.target_unit_price
          : parseFloat(String(backendItem.target_unit_price))
        : undefined,
    requiredSpecifications,
    specsList,
    manufacturerPreference: backendItem.manufacturer_preference || '',
    modelPreference: backendItem.model_preference || '',
    requiredDeliveryDate: backendItem.required_delivery_date || '',
    notes: backendItem.notes || '',
  };
}

export function adaptBackendRfq(backendRfq: BackendRfqDetail | BackendRfqListItem): Rfq {
  const items =
    'items' in backendRfq && Array.isArray(backendRfq.items)
      ? backendRfq.items.map((item, idx) => adaptBackendRfqItem(item, idx))
      : [];

  const calculatedBudget = items.reduce(
    (sum, item) => sum + (item.quantity || 0) * (item.targetUnitPrice || 0),
    0
  );
  const backendTarget = (backendRfq as any).target_budget;
  const targetBudget =
    typeof backendTarget === 'number' && backendTarget > 0
      ? backendTarget
      : calculatedBudget > 0
      ? calculatedBudget
      : 0;

  return {
    id: backendRfq.id,
    rfqNumber: backendRfq.rfq_number,
    title: backendRfq.title,
    description: backendRfq.description || '',
    requiredDeliveryDate: backendRfq.required_delivery_date || '',
    currency: (backendRfq.currency as any) || 'USD',
    status: backendRfq.status,
    statusDisplay: backendRfq.status_display,
    notes: 'notes' in backendRfq ? backendRfq.notes || '' : '',
    createdAt: backendRfq.created_at,
    updatedAt: backendRfq.updated_at,
    targetBudget,
    itemsCount: 'items_count' in backendRfq ? backendRfq.items_count : items.length,
    items,
    quotes: [],
  };
}
