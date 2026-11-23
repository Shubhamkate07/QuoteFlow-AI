export interface DashboardMetrics {
  activeRfqs: number;
  activeRfqsChange: string;
  pendingQuotes: number;
  pendingQuotesAlertCount: number;
  completedComparisons: number;
  totalIdentifiedSavings: number;
  savingsPercentage: number;
  processingDocuments: number;
  processingEngineStatus: 'online' | 'degraded' | 'idle';
}

export interface RecentRfq {
  id: string;
  code: string;
  title: string;
  category: string;
  targetBaseline: number;
  lowestQuote: number | null;
  itemsCount: number;
  quotesReceived: number;
  quotesInvited: number;
  deadline: string;
  status: 'draft' | 'open' | 'under_review' | 'completed';
}

export interface SupplierComparisonSummary {
  id: string;
  rfqCode: string;
  title: string;
  recommendedSupplier: string;
  specMatchScore: number; // e.g. 98%
  baselineCost: number;
  bestCost: number;
  savingsAmount: number;
  savingsPercentage: number;
  deliveryDaysVariance: number; // e.g. +3 days
  riskLevel: 'low' | 'moderate' | 'high';
  riskSummary?: string;
  completedAt: string;
}

export interface ActivityItem {
  id: string;
  type: 'extraction' | 'upload' | 'rfq_created' | 'approval' | 'risk_flag';
  title: string;
  description: string;
  timestamp: string;
  user?: string;
  rfqCode?: string;
}
