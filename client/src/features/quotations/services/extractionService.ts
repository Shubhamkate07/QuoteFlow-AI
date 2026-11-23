import api from '../../../lib/api';
import type {
  BackendQuotationExtraction,
  ExtractionCorrection,
  SaveCorrectionsPayload,
  ApproveExtractionPayload,
} from '../types/extraction';

export const extractionService = {
  /**
   * Fetches quotation extractions with optional query filters.
   */
  getExtractions: async (params?: {
    quotation?: string;
    document?: string;
    status?: string;
    review_status?: string;
    is_approved?: boolean;
  }): Promise<BackendQuotationExtraction[]> => {
    const response = await api.get<BackendQuotationExtraction[]>('/extractions/', {
      params,
    });
    return response.data;
  },

  /**
   * Retrieves single quotation extraction by ID with full line items, evidence, and validation flags.
   */
  getExtractionById: async (id: string): Promise<BackendQuotationExtraction> => {
    const response = await api.get<BackendQuotationExtraction>(`/extractions/${id}/`);
    return response.data;
  },

  /**
   * Triggers AI extraction on a specific uploaded QuotationDocument.
   */
  triggerExtraction: async (
    documentId: string,
    sync: boolean = true,
    model?: string
  ): Promise<BackendQuotationExtraction> => {
    const response = await api.post(`/extractions/document/${documentId}/`, {
      sync,
      model,
    });
    return response.data;
  },

  /**
   * Saves human corrections to supplier, quotation totals, line items, and commercial terms.
   * Logs an audit record for each changed field and re-computes deterministic validation.
   */
  saveCorrections: async (
    id: string,
    payload: SaveCorrectionsPayload
  ): Promise<{ status: string; message: string; extraction: BackendQuotationExtraction }> => {
    const response = await api.post(`/extractions/${id}/correct/`, payload);
    return response.data;
  },

  /**
   * Explicitly marks specified field paths as reviewed by the human reviewer.
   */
  markFieldsReviewed: async (
    id: string,
    fields: string[]
  ): Promise<{ status: string; message: string; reviewed_fields: string[]; review_status: string }> => {
    const response = await api.post(`/extractions/${id}/mark-reviewed/`, { fields });
    return response.data;
  },

  /**
   * Approves the extraction for procurement execution.
   */
  approveExtraction: async (
    id: string,
    payload?: ApproveExtractionPayload
  ): Promise<{ status: string; message: string; extraction: BackendQuotationExtraction; quotation?: any }> => {
    const response = await api.post(`/extractions/${id}/approve/`, payload || {});
    return response.data;
  },

  /**
   * Rejects the extraction with required reason.
   */
  rejectExtraction: async (
    id: string,
    reason: string
  ): Promise<{ status: string; message: string; extraction: BackendQuotationExtraction }> => {
    const response = await api.post(`/extractions/${id}/reject/`, { reason });
    return response.data;
  },

  /**
   * Retrieves complete chronological audit history of all human corrections.
   */
  getAuditHistory: async (
    id: string
  ): Promise<{ extraction_id: string; corrections_count: number; corrections: ExtractionCorrection[] }> => {
    const response = await api.get(`/extractions/${id}/audit-history/`);
    return response.data;
  },

  /**
   * Retrieves pristine original AI extraction data alongside current working data.
   */
  getOriginalData: async (
    id: string
  ): Promise<{
    extraction_id: string;
    has_human_corrections: boolean;
    corrections_count: number;
    original_extracted_data: Record<string, any>;
    current_working_data: Record<string, any>;
  }> => {
    const response = await api.get(`/extractions/${id}/original-data/`);
    return response.data;
  },

  /**
   * Synchronizes verified extraction data into the official Quotation and QuotationItem records.
   */
  applyToQuotation: async (
    id: string,
    replaceItems: boolean = true
  ): Promise<{ status: string; message: string; quotation: any }> => {
    const response = await api.post(`/extractions/${id}/apply/`, {
      replace_items: replaceItems,
    });
    return response.data;
  },
};
