import api from '../../../lib/api';
import type {
  BackendComparisonResponse,
  ScoringWeightsConfig,
  BackendPriceComparisonData,
  BackendSpecMatchingData,
  BackendQuotationRiskReport,
  BackendScoringData,
  BackendSupplierCard,
} from '../types';

export interface GenerateComparisonPayload {
  weights?: Partial<ScoringWeightsConfig>;
  comparison_currency?: string;
  conversion_date?: string;
  approved_only?: boolean;
  include_incompatible?: boolean;
  save_snapshot?: boolean;
}

export interface ComparisonWeightsResponse {
  rfq_id: string;
  rfq_number: string;
  weights: ScoringWeightsConfig;
  default_weights: ScoringWeightsConfig;
  is_customized: boolean;
  factors: Array<{
    factor: string;
    name: string;
    description: string;
  }>;
  approved_only: boolean;
  comparison_currency: string;
}

export interface UpdateWeightsPayload {
  weights: ScoringWeightsConfig;
  regenerate?: boolean;
}

export interface UpdateWeightsResponse {
  detail: string;
  rfq_id: string;
  weights: ScoringWeightsConfig;
  setting: any;
  comparison?: BackendComparisonResponse;
}

export interface SupplierComparisonMatrixResponse {
  rfq_id: string;
  rfq_number: string;
  rfq_title: string;
  comparison_currency: string;
  quotations_summary: any;
  supplier_comparison: BackendSupplierCard[];
}

/**
 * Service methods connecting Supplier Comparison features to Django backend endpoints
 */
export const comparisonApi = {
  /**
   * Retrieves comprehensive comparison data for an RFQ
   */
  async getRfqComparison(
    rfqId: string,
    options?: { refresh?: boolean; cached?: boolean; approvedOnly?: boolean; targetCurrency?: string }
  ): Promise<BackendComparisonResponse> {
    const params: Record<string, any> = {};
    if (options?.refresh) params.refresh = 'true';
    if (options?.cached) params.cached = 'true';
    if (options?.approvedOnly !== undefined) params.approved_only = options.approvedOnly;
    if (options?.targetCurrency) params.comparison_currency = options.targetCurrency;

    const response = await api.get<BackendComparisonResponse>(`/comparisons/rfqs/${rfqId}/`, {
      params,
    });
    return response.data;
  },

  /**
   * Generates or regenerates comparison with explicit options payload
   */
  async generateRfqComparison(
    rfqId: string,
    payload?: GenerateComparisonPayload
  ): Promise<BackendComparisonResponse> {
    const response = await api.post<BackendComparisonResponse>(
      `/comparisons/rfqs/${rfqId}/generate/`,
      payload || {}
    );
    return response.data;
  },

  /**
   * Forces recomputation of comparison using latest quotation data
   */
  async regenerateRfqComparison(rfqId: string): Promise<BackendComparisonResponse> {
    const response = await api.post<BackendComparisonResponse>(
      `/comparisons/rfqs/${rfqId}/regenerate/`
    );
    return response.data;
  },

  /**
   * Fetches active scoring weights for an RFQ
   */
  async getComparisonWeights(rfqId: string): Promise<ComparisonWeightsResponse> {
    const response = await api.get<ComparisonWeightsResponse>(
      `/comparisons/rfqs/${rfqId}/weights/`
    );
    return response.data;
  },

  /**
   * Updates customizable scoring weights for an RFQ and optionally re-scores immediately
   */
  async updateComparisonWeights(
    rfqId: string,
    payload: UpdateWeightsPayload
  ): Promise<UpdateWeightsResponse> {
    const response = await api.put<UpdateWeightsResponse>(
      `/comparisons/rfqs/${rfqId}/weights/`,
      payload
    );
    return response.data;
  },

  /**
   * Retrieves side-by-side vendor matrix
   */
  async getSupplierComparisonMatrix(
    rfqId: string,
    refresh?: boolean
  ): Promise<SupplierComparisonMatrixResponse> {
    const response = await api.get<SupplierComparisonMatrixResponse>(
      `/comparisons/rfqs/${rfqId}/suppliers/`,
      { params: refresh ? { refresh: 'true' } : {} }
    );
    return response.data;
  },

  /**
   * Retrieves itemized price comparison schedule
   */
  async getPriceComparison(
    rfqId: string,
    refresh?: boolean
  ): Promise<BackendPriceComparisonData> {
    const response = await api.get<BackendPriceComparisonData>(
      `/comparisons/rfqs/${rfqId}/price/`,
      { params: refresh ? { refresh: 'true' } : {} }
    );
    return response.data;
  },

  /**
   * Retrieves technical specification matching matrix
   */
  async getSpecsComparison(
    rfqId: string,
    useAi?: boolean
  ): Promise<BackendSpecMatchingData> {
    const response = await api.get<BackendSpecMatchingData>(
      `/comparisons/rfqs/${rfqId}/specs/`,
      { params: useAi ? { use_ai: 'true' } : {} }
    );
    return response.data;
  },

  /**
   * Retrieves risk flags report for an RFQ
   */
  async getRiskFlags(rfqId: string): Promise<BackendQuotationRiskReport[]> {
    const response = await api.get<BackendQuotationRiskReport[]>(
      `/comparisons/rfqs/${rfqId}/risk-flags/`
    );
    return response.data;
  },

  /**
   * Retrieves multi-criteria scoring rankings and factor explanations
   */
  async getScoring(rfqId: string): Promise<BackendScoringData> {
    const response = await api.get<BackendScoringData>(
      `/comparisons/rfqs/${rfqId}/scoring/`
    );
    return response.data;
  },

  /**
   * Downloads the executive 5-sheet Excel workbook for an RFQ
   */
  async downloadRfqComparisonExcel(rfqId: string): Promise<Blob> {
    const response = await api.get(`/comparisons/rfqs/${rfqId}/export/excel/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Downloads the publication-grade PDF comparison report for an RFQ
   */
  async downloadRfqComparisonPdf(rfqId: string): Promise<Blob> {
    const response = await api.get(`/comparisons/rfqs/${rfqId}/export/pdf/`, {
      responseType: 'blob',
    });
    return response.data;
  },
};
