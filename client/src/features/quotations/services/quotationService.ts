import api, { toRelativeApiPath } from '../../../lib/api';
import type { PaginatedResponse } from '../../../types/api';
import type {
  Quotation,
  QuotationDocument,
  BackendQuotation,
  BackendQuotationDocument,
  UploadQuotationPayload,
} from '../types';
import { adaptBackendQuotation, adaptBackendDocument } from '../types';

export const quotationService = {
  /**
   * Fetches quotations list from backend with optional filters.
   * Automatically traverses all pages via 'next' pagination links to collect all records.
   */
  getQuotations: async (params?: { rfq?: string; supplier?: string; search?: string }): Promise<Quotation[]> => {
    const cleanParams: Record<string, string> = {};
    if (params?.rfq) cleanParams.rfq = params.rfq;
    if (params?.supplier) cleanParams.supplier = params.supplier;
    if (params?.search) cleanParams.search = params.search;

    let allResults: BackendQuotation[] = [];
    let nextUrl: string | null = '/quotations/';
    let isFirst = true;

    while (nextUrl) {
      const response: { data: BackendQuotation[] | PaginatedResponse<BackendQuotation> } = await api.get<BackendQuotation[] | PaginatedResponse<BackendQuotation>>(nextUrl, {
        params: isFirst ? cleanParams : undefined,
      });
      isFirst = false;

      if (Array.isArray(response.data)) {
        allResults = response.data;
        break;
      } else if (response.data && Array.isArray(response.data.results)) {
        allResults = allResults.concat(response.data.results);
        nextUrl = response.data.next ? toRelativeApiPath(response.data.next) : null;
      } else {
        break;
      }
    }

    return allResults.map(adaptBackendQuotation);
  },

  /**
   * Fetches quotations associated with a specific RFQ, traversing all pages.
   */
  getQuotationsByRfq: async (rfqId: string): Promise<Quotation[]> => {
    let allResults: BackendQuotation[] = [];
    let nextUrl: string | null = `/quotations/rfq/${rfqId}/`;

    while (nextUrl) {
      const response: { data: BackendQuotation[] | PaginatedResponse<BackendQuotation> } = await api.get<BackendQuotation[] | PaginatedResponse<BackendQuotation>>(nextUrl);
      if (Array.isArray(response.data)) {
        allResults = response.data;
        break;
      } else if (response.data && Array.isArray(response.data.results)) {
        allResults = allResults.concat(response.data.results);
        nextUrl = response.data.next ? toRelativeApiPath(response.data.next) : null;
      } else {
        break;
      }
    }

    return allResults.map(adaptBackendQuotation);
  },

  /**
   * Retrieves single quotation by UUID including attached documents and line items.
   */
  getQuotationById: async (id: string): Promise<Quotation> => {
    const response = await api.get<BackendQuotation>(`/quotations/${id}/`);
    return adaptBackendQuotation(response.data);
  },

  /**
   * Uploads a document and creates a new quotation record with progress callback.
   */
  uploadQuotationWithDocument: async (
    payload: UploadQuotationPayload,
    onProgress?: (percent: number) => void
  ): Promise<Quotation> => {
    const formData = new FormData();
    formData.append('rfq_id', payload.rfqId);
    formData.append('supplier_id', payload.supplierId);
    formData.append('file', payload.file);

    if (payload.quoteReference && payload.quoteReference.trim()) {
      formData.append('quotation_number', payload.quoteReference.trim());
    }
    if (payload.currency) {
      formData.append('currency', payload.currency);
    }

    const response = await api.post<BackendQuotation>('/quotations/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });

    return adaptBackendQuotation(response.data);
  },

  /**
   * Attaches a document to an existing quotation (e.g. replacing or adding docs).
   */
  attachDocument: async (
    quotationId: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<QuotationDocument> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<BackendQuotationDocument>(`/quotations/${quotationId}/documents/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });

    return adaptBackendDocument(response.data);
  },

  /**
   * Lists documents attached to a quotation.
   */
  getQuotationDocuments: async (quotationId: string): Promise<QuotationDocument[]> => {
    const response = await api.get<BackendQuotationDocument[]>(`/quotations/${quotationId}/documents/`);
    return (response.data || []).map(adaptBackendDocument);
  },

  /**
   * Downloads a document file as an authenticated Blob.
   */
  downloadDocumentBlob: async (documentId: string, inline: boolean = false): Promise<{ blob: Blob; filename: string }> => {
    const response = await api.get(`/quotations/documents/${documentId}/download/`, {
      params: inline ? { inline: 'true' } : {},
      responseType: 'blob',
    });

    let filename = 'document';
    const disposition = response.headers['content-disposition'] as string | undefined;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    return { blob: response.data as Blob, filename };
  },

  /**
   * Deletes a document record and removes file from storage.
   */
  deleteDocument: async (documentId: string): Promise<void> => {
    await api.delete(`/quotations/documents/${documentId}/`);
  },

  /**
   * Deletes a quotation and all attached items and files.
   */
  deleteQuotation: async (quotationId: string): Promise<void> => {
    await api.delete(`/quotations/${quotationId}/`);
  },

  /**
   * Updates quotation details.
   */
  updateQuotation: async (id: string, updates: Record<string, unknown>): Promise<Quotation> => {
    const response = await api.patch<BackendQuotation>(`/quotations/${id}/`, updates);
    return adaptBackendQuotation(response.data);
  },
};
