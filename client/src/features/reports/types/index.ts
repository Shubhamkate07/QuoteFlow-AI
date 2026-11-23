export interface ReportMeta {
  reportId: string;
  reportTitle: string;
  generatedAt: string;
  authorName: string;
  authorRole: string;
  rfqId: string;
  rfqNumber: string;
  rfqTitle: string;
  currency: string;
  targetBudget: number;
  requiredDeliveryDate: string;
  status: 'draft' | 'under_review' | 'approved' | 'archived';
}

export interface RecommendationSummary {
  primaryRecommendedSupplierId: string;
  primarySupplierName: string;
  primaryRationale: string;
  alternativeSupplierId?: string;
  alternativeSupplierName?: string;
  alternativeRationale?: string;
  disqualifiedSupplierId?: string;
  disqualifiedSupplierName?: string;
  disqualificationRationale?: string;
  decisionTradeoffSummary: string;
}

export interface RiskItem {
  category: 'Commercial' | 'Technical' | 'Schedule' | 'Compliance';
  severity: 'low' | 'medium' | 'high';
  supplierName: string;
  riskDescription: string;
  mitigationStrategy: string;
}

export interface ReportExportPayload {
  format: 'pdf' | 'excel';
  rfqNumber: string;
  includeLineItems: boolean;
  includeRiskMatrix: boolean;
  includeAuditSignoff: boolean;
}
