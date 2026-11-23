/**
 * TypeScript type definitions for AI Quotation Extraction,
 * Deterministic Validation Flags, Evidence Tracing, and Human Review Workflows.
 */

export type ExtractionStatus = 'pending' | 'processing' | 'completed' | 'partial' | 'failed';

export type ReviewStatus = 'unreviewed' | 'in_review' | 'changes_requested' | 'approved' | 'rejected';

export type ValidationSeverity = 'ERROR' | 'WARNING' | 'INFO';

export interface ValidationFlag {
  flag_type: string;
  severity: ValidationSeverity;
  field: string;
  expected_value?: any;
  actual_value?: any;
  explanation: string;
}

export interface FieldEvidence {
  extracted_value?: any;
  source_text?: string;
  page_number?: number;
  confidence_level?: number;
}

export interface SpecificationItem {
  name: string;
  value: string;
}

export interface ExtractedLineItemData {
  line_number?: number;
  description: string;
  manufacturer?: string;
  model?: string;
  quantity: number;
  unit?: string;
  unit_price: number;
  discount?: number;
  tax?: number;
  total: number;
  specifications?: SpecificationItem[];
  source_text?: string;
  page_number?: number;
  confidence_level?: number;
}

export interface ExtractedSupplierData {
  supplier_name?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  quotation_number?: string;
}

export interface ExtractedQuotationData {
  quotation_date?: string;
  validity_date?: string;
  currency?: string;
  subtotal?: number;
  tax?: number;
  discount?: number;
  shipping?: number;
  grand_total?: number;
}

export interface ExtractedCommercialTermsData {
  delivery_time?: string;
  delivery_terms?: string;
  payment_terms?: string;
  warranty?: string;
  notes?: string;
}

export interface ExtractionCorrection {
  id: string;
  extraction_id: string;
  correction_type: string;
  field_path: string;
  previous_value: any;
  new_value: any;
  reason?: string;
  corrected_by_email?: string;
  created_at: string;
}

export interface BackendQuotationExtraction {
  id: string;
  document_id: string;
  document_filename: string;
  quotation_id: string | null;
  status: ExtractionStatus;
  review_status: ReviewStatus;
  is_approved: boolean;
  model_name: string;
  supplier_name: string;
  quotation_number: string;
  contact_person?: string;
  contact_email?: string;
  contact_phone?: string;
  supplier_address?: string;
  quotation_date?: string | null;
  validity_date?: string | null;
  currency: string;
  delivery_time?: string;
  delivery_terms?: string;
  payment_terms?: string;
  warranty?: string;
  notes?: string;
  stated_subtotal?: number | string | null;
  stated_tax?: number | string | null;
  stated_discount?: number | string | null;
  stated_shipping?: number | string | null;
  stated_grand_total?: number | string | null;
  calculated_items_subtotal?: number | string | null;
  calculated_grand_total?: number | string | null;
  total_variance?: number | string | null;
  is_math_consistent: boolean;
  validation_warnings: any[];
  validation_flags: ValidationFlag[];
  items_count: number;
  overall_confidence: number;
  processing_time_ms: number;
  task_id?: string;
  error_message?: string;
  reviewed_by_email?: string | null;
  reviewed_at?: string | null;
  approved_by_email?: string | null;
  approved_at?: string | null;
  review_notes?: string;
  reviewed_fields: string[];
  has_human_corrections: boolean;
  corrections_count: number;
  recent_corrections: ExtractionCorrection[];
  is_applied_to_quotation: boolean;
  applied_at?: string | null;
  applied_by_email?: string | null;
  extracted_data: {
    supplier?: ExtractedSupplierData;
    quotation?: ExtractedQuotationData;
    commercial_terms?: ExtractedCommercialTermsData;
    line_items?: ExtractedLineItemData[];
    evidence?: Record<string, FieldEvidence>;
    overall_confidence?: number;
    summary?: string;
  };
  original_extracted_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SaveCorrectionsPayload {
  supplier?: Partial<ExtractedSupplierData>;
  quotation?: Partial<ExtractedQuotationData>;
  commercial_terms?: Partial<ExtractedCommercialTermsData>;
  line_items?: ExtractedLineItemData[];
  reason?: string;
  mark_reviewed?: boolean;
}

export interface ApproveExtractionPayload {
  review_notes?: string;
  apply_to_quotation?: boolean;
}
