export type ComparisonSortOption =
  | 'highest_score'
  | 'lowest_price'
  | 'highest_spec'
  | 'shortest_lead';

export type ComparisonViewTab = 'matrix' | 'price' | 'specs' | 'risk';

export type DataOriginType =
  | 'extracted'
  | 'calculated'
  | 'ai'
  | 'risk'
  | 'decision';

/* =========================================================================
   Scoring Weights Config (Must strictly sum to 100%)
========================================================================= */
export interface ScoringWeightsConfig {
  price: number;
  spec_match: number;
  delivery: number;
  payment_terms: number;
  warranty: number;
}

export const DEFAULT_WEIGHTS: ScoringWeightsConfig = {
  price: 40,
  spec_match: 30,
  delivery: 15,
  payment_terms: 10,
  warranty: 5,
};

export interface WeightPreset {
  id: string;
  name: string;
  description: string;
  weights: ScoringWeightsConfig;
}

export const WEIGHT_PRESETS: WeightPreset[] = [
  {
    id: 'balanced',
    name: 'Balanced Default',
    description: '40% Price, 30% Specs, 15% Delivery, 10% Terms, 5% Warranty',
    weights: { price: 40, spec_match: 30, delivery: 15, payment_terms: 10, warranty: 5 },
  },
  {
    id: 'cost_focused',
    name: 'Cost-Driven',
    description: '55% Price, 25% Specs, 10% Delivery, 5% Terms, 5% Warranty',
    weights: { price: 55, spec_match: 25, delivery: 10, payment_terms: 5, warranty: 5 },
  },
  {
    id: 'specs_focused',
    name: 'Technical & Quality Priority',
    description: '25% Price, 50% Specs, 15% Delivery, 5% Terms, 5% Warranty',
    weights: { price: 25, spec_match: 50, delivery: 15, payment_terms: 5, warranty: 5 },
  },
  {
    id: 'lead_time_focused',
    name: 'Urgent Delivery Schedule',
    description: '30% Price, 25% Specs, 35% Delivery, 5% Terms, 5% Warranty',
    weights: { price: 30, spec_match: 25, delivery: 35, payment_terms: 5, warranty: 5 },
  },
];

/* =========================================================================
   Backend API Data Types (Matching QuoteFlow AI Comparisons Engine)
========================================================================= */

export interface BackendScoreFactor {
  factor: 'price' | 'spec_match' | 'delivery' | 'payment_terms' | 'warranty';
  name?: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  explanation: string;
  metrics?: Record<string, any>;
}

export interface BackendSupplierCard {
  rank: number | null;
  supplier_id: string;
  supplier_name: string;
  quotation_id: string;
  quotation_number: string;
  review_status: {
    is_approved: boolean;
    description: string;
    metadata?: any;
  };
  pricing: {
    currency: string;
    subtotal: number | null;
    tax_amount: number | null;
    shipping_amount: number | null;
    discount_amount: number | null;
    grand_total: number;
    price_difference_from_lowest: number | null;
    percentage_difference_from_lowest: number | null;
    is_lowest_price: boolean;
  };
  specifications: {
    compliance_score: number;
    overall_verdict: string;
    total_critical_mismatches: number;
  };
  delivery: {
    delivery_terms: string;
    lead_time_weeks: number;
    on_time_status: 'On Schedule' | 'Delayed' | string;
  };
  commercial_terms: {
    payment_terms: string;
    warranty_information: string;
  };
  risk_profile: {
    total_flags_count: number;
    high_severity_count: number;
    overall_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  };
  scoring: {
    final_score: number;
    is_recommended_for_consideration: boolean;
    advisory_notes: string[];
    factors: Record<string, BackendScoreFactor>;
  };
}

export interface BackendUnreviewedQuotation {
  quotation_id: string;
  quotation_number: string;
  supplier_name: string;
  status: string;
  reason: string;
}

export interface BackendQuotationsSummary {
  total_active_quotations: number;
  compared_quotations_count: number;
  unreviewed_quotations_count: number;
  unreviewed_quotations: BackendUnreviewedQuotation[];
}

export interface BackendPriceQuotationItem {
  quotation_item_id: string;
  rfq_item_id: string;
  item_name: string;
  quoted_quantity: number;
  quoted_unit_price: number;
  extended_price: number;
  is_compatible: boolean;
  is_lowest_for_item: boolean;
}

export interface BackendPriceQuotation {
  quotation_id: string;
  quotation_number: string;
  supplier_id: string;
  supplier_name: string;
  is_approved: boolean;
  is_lowest_price: boolean;
  grand_total: number;
  subtotal: number | null;
  tax_amount: number | null;
  shipping_amount: number | null;
  discount_amount: number | null;
  price_difference_from_lowest: number | null;
  percentage_difference_from_lowest: number | null;
  items: BackendPriceQuotationItem[];
}

export interface BackendPriceItemRowQuote {
  quotation_id: string;
  quotation_number: string;
  supplier_id: string;
  supplier_name: string;
  unit_price: number;
  extended_price: number;
  is_lowest: boolean;
  is_compatible: boolean;
}

export interface BackendPriceItemRow {
  rfq_item_id: string;
  item_name: string;
  quantity: number;
  uom: string;
  target_unit_price: number | null;
  target_extended_price: number | null;
  lowest_unit_price: number | null;
  lowest_extended_price: number | null;
  quotes: BackendPriceItemRowQuote[];
}

export interface BackendPriceComparisonData {
  rfq_id: string;
  rfq_number: string;
  rfq_title: string;
  comparison_currency: string;
  quotations_compared_count: number;
  lowest_grand_total: number | null;
  highest_grand_total: number | null;
  max_savings_amount: number;
  max_savings_percentage: number;
  cherry_pick_total: number;
  cherry_pick_savings: number;
  items_matrix: BackendPriceItemRow[];
  quotations: BackendPriceQuotation[];
  warnings?: string[];
}

export interface BackendSpecParameterMatch {
  parameter: string;
  rfq_value: string;
  supplier_value: string;
  status: 'EXACT_MATCH' | 'MISMATCH' | 'MISSING' | 'UNCLEAR' | 'ADDITIONAL' | string;
  explanation: string;
  evidence: string;
}

export interface BackendSpecSupplierMatch {
  supplier_id: string;
  supplier_name: string;
  quotation_id: string;
  quotation_number: string;
  quotation_item_id: string;
  compliance_score: number;
  overall_status: 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NON_COMPLIANT' | string;
  exact_matches: number;
  mismatches: number;
  missing_specifications: number;
  unclear_specifications: number;
  additional_specifications: number;
  parameter_matches: BackendSpecParameterMatch[];
}

export interface BackendSpecItemMatrix {
  rfq_item_id: string;
  rfq_item_name: string;
  rfq_specs: Record<string, string>;
  supplier_matches: BackendSpecSupplierMatch[];
}

export interface BackendSpecSupplierSummary {
  supplier_id: string;
  supplier_name: string;
  quotation_id: string;
  quotation_number?: string;
  average_score: number;
  overall_verdict: 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NON_COMPLIANT' | string;
  total_critical_mismatches: number;
  compliant_items_count: number;
  partially_compliant_items_count: number;
  non_compliant_items_count: number;
}

export interface BackendSpecMatchingData {
  rfq_id: string;
  rfq_number: string;
  rfq_title: string;
  items: BackendSpecItemMatrix[];
  supplier_summaries: BackendSpecSupplierSummary[];
}

export interface BackendRiskFlag {
  type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL' | string;
  title: string;
  description: string;
  affected_field: string;
  evidence: string;
  recommended_action: string;
}

export interface BackendQuotationRiskReport {
  quotation_id: string;
  quotation_number: string;
  supplier_id: string;
  supplier_name: string;
  overall_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  flags: BackendRiskFlag[];
}

export interface BackendScoringRanking {
  rank: number;
  quotation_id: string;
  quotation_number: string;
  supplier_id: string;
  supplier_name: string;
  final_score: number;
  is_recommended_for_consideration: boolean;
  advisory_notes: string[];
  factors: Record<string, BackendScoreFactor>;
}

export interface BackendScoringData {
  rfq_id: string;
  rfq_number: string;
  weights_applied: ScoringWeightsConfig;
  rankings: BackendScoringRanking[];
  scoring_limitations: string[];
  disclaimer: string;
}

export interface BackendComparisonSettings {
  approved_only: boolean;
  include_incompatible: boolean;
  weights: ScoringWeightsConfig;
  comparison_currency?: string;
}

export interface BackendComparisonResponse {
  rfq_id: string;
  rfq_number: string;
  rfq_title: string;
  comparison_currency: string;
  generated_at: string;
  quotations_summary: BackendQuotationsSummary;
  supplier_comparison: BackendSupplierCard[];
  price_comparison: BackendPriceComparisonData;
  specification_matching: BackendSpecMatchingData;
  risk_flags: BackendQuotationRiskReport[];
  scoring: BackendScoringData;
  settings: BackendComparisonSettings;
  decision_support_guardrail: {
    automated_purchase_enabled: boolean;
    statement: string;
  };
  scoring_system_limitations: string[];
}

/* =========================================================================
   Frontend Visual Adapter Models (Used in tables, drawers & summary cards)
========================================================================= */

export interface ComparisonLineItemCell {
  unitPrice: number;
  totalPrice: number;
  materialSpec: string;
  confidenceScore: number;
  isLowestUnitPrice: boolean;
  hasVariance: boolean;
  discrepancyNote?: string;
}

export interface ScoreFactorBreakdown {
  id: 'price' | 'spec_match' | 'delivery' | 'payment_terms' | 'warranty';
  factorName: string;
  weightPercentage: number;
  rawScore: number;
  weightedScore: number;
  rationale: string;
  metrics?: Record<string, any>;
}

export interface ComparisonSupplierBid {
  quotationId: string;
  supplierId: string;
  supplierName: string;
  supplierCategory?: string;
  quoteReference: string;
  quoteDate?: string;
  fileName: string;
  fileSize: string;
  status: string;
  currency: string;
  isApproved: boolean;

  // Commercial & Financial
  totalAmount: number;
  isLowestTotalAmount: boolean;
  varianceVsBudget: number;
  variancePercentage: number;
  subtotal: number | null;
  taxAmount: number | null;
  shippingAmount: number | null;
  discountAmount: number | null;
  paymentTerms: string;

  // Logistics & Terms
  deliveryLeadWeeks: number;
  isShortestLeadTime: boolean;
  onTimeStatus: string;
  incoterms: string;
  warrantyTerms: string;

  // Compliance & Risk
  specMatchPercentage: number;
  isHighestSpecMatch: boolean;
  criticalMismatchesCount: number;
  materialDeviations: string[];
  missingFields: string[];
  riskLevel: 'low' | 'medium' | 'high';
  riskFlags: string[];
  riskFlagDetails: BackendRiskFlag[];

  // Explainable Score
  overallScore: number;
  rank: number;
  recommendationTag?: string;
  scoreBreakdown: ScoreFactorBreakdown[];

  // BOM Line Items Breakdown (keyed by rfqItemId)
  lineItemsMap: Record<string, ComparisonLineItemCell>;
}

export interface ComparisonFilterState {
  selectedRfqId: string;
  sortBy: ComparisonSortOption;
  minSpecMatch: number;
  maxLeadWeeks: number;
  riskFilter: 'all' | 'low_risk_only';
  approvedOnly: boolean;
  visibleSupplierIds: string[];
}
