import api, { toRelativeApiPath } from '../../../lib/api';
import type { PaginatedResponse } from '../../../types/api';
import type {
  Rfq,
  RfqItem,
  BackendRfqDetail,
  BackendRfqItem,
  RfqQueryParams,
  CreateRfqPayload,
  UpdateRfqPayload,
  CreateRfqItemPayload,
  UpdateRfqItemPayload,
} from '../types';
import { adaptBackendRfq, adaptBackendRfqItem } from '../types';
import type { RfqFormValues, RfqItemFormValues } from '../schemas/rfqSchema';

export const rfqService = {
  /**
   * Fetches paginated list of RFQs with optional search, status, and currency filters.
   * If no page is specified, follows 'next' links to collect all pages.
   */
  getRfqs: async (params?: RfqQueryParams): Promise<PaginatedResponse<Rfq>> => {
    const cleanParams: Record<string, any> = {};
    if (params?.search?.trim()) cleanParams.search = params.search.trim();
    if (params?.status && params.status !== 'all') cleanParams.status = params.status;
    if (params?.currency && params.currency !== 'all') cleanParams.currency = params.currency;
    if (params?.page) cleanParams.page = params.page;

    // Single page requested (e.g. paginated table view)
    if (params?.page) {
      const response = await api.get<any>('/rfqs/', {
        params: cleanParams,
      });

      const rawData = response.data;
      const items = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

      return {
        count: typeof rawData?.count === 'number' ? rawData.count : items.length,
        next: rawData?.next || null,
        previous: rawData?.previous || null,
        results: items.map((item: any) => adaptBackendRfq(item)),
      };
    }

    // No page specified: follow `next` to collect all pages
    let allItems: any[] = [];
    let nextUrl: string | null = '/rfqs/';
    let totalCount = 0;
    let isFirst = true;

    while (nextUrl) {
      const response: { data: any } = await api.get<any>(nextUrl, {
        params: isFirst ? cleanParams : undefined,
      });
      isFirst = false;

      const rawData = response.data;
      if (Array.isArray(rawData)) {
        allItems = rawData;
        totalCount = rawData.length;
        break;
      }
      if (typeof rawData?.count === 'number') {
        totalCount = rawData.count;
      }
      if (Array.isArray(rawData?.results)) {
        allItems = allItems.concat(rawData.results);
      }
      nextUrl = rawData?.next ? toRelativeApiPath(rawData.next) : null;
    }

    return {
      count: totalCount || allItems.length,
      next: null,
      previous: null,
      results: allItems.map((item: any) => adaptBackendRfq(item)),
    };
  },

  /**
   * Retrieves full RFQ detail including BOM line items and specifications
   */
  getRfqById: async (id: string): Promise<Rfq> => {
    const response = await api.get<BackendRfqDetail>(`/rfqs/${id}/`);
    return adaptBackendRfq(response.data);
  },

  /**
   * Creates a new RFQ
   */
  createRfq: async (values: RfqFormValues): Promise<Rfq> => {
    const payload: CreateRfqPayload = {
      title: values.title.trim(),
      description: values.description?.trim() || '',
      currency: values.currency,
      status: values.status,
      required_delivery_date: values.requiredDeliveryDate || null,
      notes: values.notes?.trim() || '',
    };

    if (values.rfqNumber?.trim()) {
      payload.rfq_number = values.rfqNumber.trim();
    }

    const response = await api.post<BackendRfqDetail>('/rfqs/', payload);
    return adaptBackendRfq(response.data);
  },

  /**
   * Updates an existing RFQ header fields
   */
  updateRfq: async (id: string, values: Partial<RfqFormValues>): Promise<Rfq> => {
    const payload: UpdateRfqPayload = {};
    if (values.title !== undefined) payload.title = values.title.trim();
    if (values.rfqNumber !== undefined && values.rfqNumber.trim()) payload.rfq_number = values.rfqNumber.trim();
    if (values.description !== undefined) payload.description = values.description.trim();
    if (values.currency !== undefined) payload.currency = values.currency;
    if (values.status !== undefined) payload.status = values.status;
    if (values.requiredDeliveryDate !== undefined) payload.required_delivery_date = values.requiredDeliveryDate || null;
    if (values.notes !== undefined) payload.notes = values.notes.trim();

    const response = await api.patch<BackendRfqDetail>(`/rfqs/${id}/`, payload);
    return adaptBackendRfq(response.data);
  },

  /**
   * Deletes an RFQ
   */
  deleteRfq: async (id: string): Promise<void> => {
    await api.delete(`/rfqs/${id}/`);
  },

  /**
   * Lists line items for an RFQ
   */
  getRfqItems: async (rfqId: string): Promise<RfqItem[]> => {
    const response = await api.get<BackendRfqItem[]>(`/rfqs/${rfqId}/items/`);
    return (response.data || []).map((item, idx) => adaptBackendRfqItem(item, idx));
  },

  /**
   * Adds a line item to an RFQ with nested technical specifications
   */
  addRfqItem: async (rfqId: string, values: RfqItemFormValues): Promise<RfqItem> => {
    const specifications: CreateRfqItemPayload['specifications'] = [];

    // Parse structured specifications
    if (values.specsList && values.specsList.length > 0) {
      for (const spec of values.specsList) {
        if (spec.key?.trim() && spec.value?.trim()) {
          specifications.push({
            parameter_name: spec.key.trim(),
            required_value: spec.value.trim(),
            importance: 'mandatory',
          });
        }
      }
    }

    // Include primary specification text if provided
    if (specifications.length === 0 && values.requiredSpecifications?.trim()) {
      specifications.push({
        parameter_name: 'Primary Specification',
        required_value: values.requiredSpecifications.trim(),
        importance: 'mandatory',
      });
    }

    const payload: CreateRfqItemPayload = {
      item_name: values.name.trim(),
      quantity: values.quantity,
      unit: values.unit?.trim() || 'PCS',
      description: values.description?.trim() || '',
      target_unit_price:
        values.targetUnitPrice !== undefined && values.targetUnitPrice !== null && !isNaN(values.targetUnitPrice)
          ? values.targetUnitPrice
          : null,
      manufacturer_preference: values.manufacturerPreference?.trim() || '',
      model_preference: values.modelPreference?.trim() || '',
      required_delivery_date: values.requiredDeliveryDate || null,
      notes: values.notes?.trim() || '',
      custom_specifications: {
        required_spec_summary: values.requiredSpecifications?.trim() || '',
      },
      specifications,
    };

    const response = await api.post<BackendRfqItem>(`/rfqs/${rfqId}/items/`, payload);
    return adaptBackendRfqItem(response.data);
  },

  /**
   * Updates an existing line item on an RFQ
   */
  updateRfqItem: async (
    rfqId: string,
    itemId: string,
    values: Partial<RfqItemFormValues>
  ): Promise<RfqItem> => {
    const payload: UpdateRfqItemPayload = {};

    if (values.name !== undefined) payload.item_name = values.name.trim();
    if (values.quantity !== undefined) payload.quantity = values.quantity;
    if (values.unit !== undefined) payload.unit = values.unit.trim();
    if (values.description !== undefined) payload.description = values.description.trim();
    if (values.targetUnitPrice !== undefined) {
      payload.target_unit_price =
        values.targetUnitPrice !== null && !isNaN(values.targetUnitPrice)
          ? values.targetUnitPrice
          : null;
    }
    if (values.manufacturerPreference !== undefined) {
      payload.manufacturer_preference = values.manufacturerPreference.trim();
    }
    if (values.modelPreference !== undefined) {
      payload.model_preference = values.modelPreference.trim();
    }
    if (values.requiredDeliveryDate !== undefined) {
      payload.required_delivery_date = values.requiredDeliveryDate || null;
    }
    if (values.notes !== undefined) payload.notes = values.notes.trim();

    if (values.requiredSpecifications !== undefined) {
      payload.custom_specifications = {
        required_spec_summary: values.requiredSpecifications.trim(),
      };
    }

    if (values.specsList !== undefined) {
      payload.specifications = values.specsList
        .filter((s) => Boolean(s.key?.trim() && s.value?.trim()))
        .map((s) => ({
          parameter_name: s.key!.trim(),
          required_value: s.value!.trim(),
          importance: 'mandatory',
        }));

      if (payload.specifications.length === 0 && values.requiredSpecifications?.trim()) {
        payload.specifications.push({
          parameter_name: 'Primary Specification',
          required_value: values.requiredSpecifications.trim(),
          importance: 'mandatory',
        });
      }
    }

    const response = await api.patch<BackendRfqItem>(`/rfqs/${rfqId}/items/${itemId}/`, payload);
    return adaptBackendRfqItem(response.data);
  },

  /**
   * Deletes a line item from an RFQ
   */
  deleteRfqItem: async (rfqId: string, itemId: string): Promise<void> => {
    await api.delete(`/rfqs/${rfqId}/items/${itemId}/`);
  },
};
