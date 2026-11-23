import api from '../../../lib/api';
import type { DashboardMetrics, RecentRfq, SupplierComparisonSummary, ActivityItem } from '../types';

export interface BackendDashboardOverview {
  organization: {
    id: string;
    name: string;
  };
  metrics: {
    activeRfqs: number;
    totalRfqs: number;
    completedRfqs: number;
    quotesPendingReview: number;
    quotesVerified: number;
    totalQuotations: number;
    activeSuppliers: number;
    potentialSavingsTotal: number;
    savingsPercentage: number;
    accuracyRate: number;
    avgCycleDays: number;
  };
  recentRfqs: RecentRfq[];
  recentComparisons: Array<{
    id: string;
    rfqId: string;
    rfqCode: string;
    rfqTitle: string;
    suppliersCount: number;
    leadingSupplier: string;
    leadingScore: number;
    lowestBid: number;
    potentialSavings: number;
    comparisonDate: string;
    status: string;
  }>;
  activities: Array<{
    id: string;
    type: string;
    title: string;
    description: string;
    timestamp: string;
    rfqCode?: string;
  }>;
}

export interface DashboardOverviewData {
  organization: {
    id: string;
    name: string;
  };
  metrics: DashboardMetrics;
  recentRfqs: RecentRfq[];
  recentComparisons: SupplierComparisonSummary[];
  activities: ActivityItem[];
}

export const dashboardService = {
  /**
   * Fetches real-time dashboard procurement metrics, recent RFQs,
   * recent comparison summaries, and activity audit feed.
   */
  getOverview: async (): Promise<DashboardOverviewData> => {
    const response = await api.get<BackendDashboardOverview>('/dashboard/overview/');
    const data = response.data;

    // Adapt metrics
    const metrics: DashboardMetrics = {
      activeRfqs: data.metrics?.activeRfqs ?? 0,
      activeRfqsChange: `${data.metrics?.totalRfqs ?? 0} total RFQs`,
      pendingQuotes: (data.metrics?.quotesPendingReview ?? 0) + (data.metrics?.quotesVerified ?? 0),
      pendingQuotesAlertCount: data.metrics?.quotesPendingReview ?? 0,
      completedComparisons: data.metrics?.completedRfqs ?? 0,
      totalIdentifiedSavings: data.metrics?.potentialSavingsTotal ?? 0,
      savingsPercentage: data.metrics?.savingsPercentage ?? 0,
      processingDocuments: data.metrics?.quotesPendingReview ?? 0,
      processingEngineStatus: 'online',
    };

    // Adapt comparisons
    const recentComparisons: SupplierComparisonSummary[] = (data.recentComparisons || []).map((comp) => {
      const bestCost = comp.lowestBid || 0;
      const savings = comp.potentialSavings || 0;
      const baseline = bestCost + savings;
      const savingsPct = baseline > 0 ? Math.round((savings / baseline) * 100) : 0;

      return {
        id: comp.id,
        rfqCode: comp.rfqCode,
        title: comp.rfqTitle,
        recommendedSupplier: comp.leadingSupplier,
        specMatchScore: Math.round(comp.leadingScore || 95),
        baselineCost: baseline,
        bestCost: bestCost,
        savingsAmount: savings,
        savingsPercentage: savingsPct,
        deliveryDaysVariance: 0,
        riskLevel: (savings > 0 ? 'low' : 'moderate') as 'low' | 'moderate' | 'high',
        completedAt: comp.comparisonDate,
      };
    });

    // Adapt activities
    const activities: ActivityItem[] = (data.activities || []).map((act) => {
      let actType: ActivityItem['type'] = 'upload';
      if (act.type === 'extraction_verified') actType = 'approval';
      else if (act.type === 'quote_received' || act.type === 'upload') actType = 'upload';
      else if (act.type === 'rfq_created') actType = 'rfq_created';
      else if (act.type === 'risk_flag') actType = 'risk_flag';
      else if (act.type === 'extraction') actType = 'extraction';

      return {
        id: act.id,
        type: actType,
        title: act.title,
        description: act.description,
        timestamp: act.timestamp,
        rfqCode: act.rfqCode,
      };
    });

    return {
      organization: data.organization,
      metrics,
      recentRfqs: data.recentRfqs || [],
      recentComparisons,
      activities,
    };
  },
};
