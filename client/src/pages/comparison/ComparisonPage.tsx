import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { ComparisonSummaryCards } from '../../features/comparison/components/ComparisonSummaryCards';
import { ComparisonFilterBar } from '../../features/comparison/components/ComparisonFilterBar';
import { ComparisonMatrixTable } from '../../features/comparison/components/ComparisonMatrixTable';
import { PriceComparisonView } from '../../features/comparison/components/PriceComparisonView';
import { SpecsMatchingView } from '../../features/comparison/components/SpecsMatchingView';
import { RiskFlagsView } from '../../features/comparison/components/RiskFlagsView';
import { ExplainableScoreModal } from '../../features/comparison/components/ExplainableScoreModal';
import { SupplierDetailDrawer } from '../../features/comparison/components/SupplierDetailDrawer';
import { CustomWeightsModal } from '../../features/comparison/components/CustomWeightsModal';
import { DataOriginBadge } from '../../features/comparison/components/DataOriginBadge';
import {
  adaptBackendComparisonToBids,
  buildComparisonData,
} from '../../features/comparison/utils/comparisonScoring';
import {
  useRfqComparison,
  useRfqComparisonWeights,
  useUpdateComparisonWeights,
  useRegenerateComparison,
} from '../../features/comparison/hooks/useComparison';
import { comparisonApi } from '../../features/comparison/api/comparisonApi';
import type {
  ComparisonFilterState,
  ComparisonSupplierBid,
  ComparisonViewTab,
  ScoringWeightsConfig,
} from '../../features/comparison/types';
import { useRfq } from '../../features/rfq/context/RfqContext';
import { useRfqDetail } from '../../features/rfq/hooks/useRfqQueries';
import { useQuotation } from '../../features/quotations/context/QuotationContext';
import { ROUTES } from '../../routes/paths';
import {
  Download,
  Info,
  Sparkles,
  ArrowUpRight,
  FileText,
  AlertCircle,
  RefreshCw,
  Plus,
} from 'lucide-react';

export const ComparisonPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { rfqs, getRfqById } = useRfq();
  const { getQuotationsByRfq } = useQuotation();

  // Query parameter support: ?rfqId=...
  const queryRfqId = searchParams.get('rfqId');
  const defaultRfqId = queryRfqId || (rfqs.length > 0 ? rfqs[0].id : '');

  const [selectedRfqId, setSelectedRfqId] = useState<string>(defaultRfqId);

  // Sync selectedRfqId when query parameter changes or when rfqs load
  useEffect(() => {
    if (queryRfqId) {
      setSelectedRfqId(queryRfqId);
    } else if ((!selectedRfqId || selectedRfqId === 'rfq-2026-0042') && rfqs.length > 0) {
      setSelectedRfqId(rfqs[0].id);
    }
  }, [queryRfqId, rfqs, selectedRfqId]);

  const { data: rfqDetail } = useRfqDetail(selectedRfqId);
  const selectedRfq = rfqDetail || getRfqById(selectedRfqId) || (rfqs.length > 0 ? rfqs[0] : undefined);

  // Active view tab state: 'matrix' | 'price' | 'specs' | 'risk'
  const [activeTab, setActiveTab] = useState<ComparisonViewTab>('matrix');

  // Filter & sorting state
  const [filterState, setFilterState] = useState<ComparisonFilterState>({
    selectedRfqId: selectedRfqId,
    sortBy: 'highest_score',
    minSpecMatch: 0,
    maxLeadWeeks: 0,
    riskFilter: 'all',
    approvedOnly: true,
    visibleSupplierIds: [],
  });

  // Keep filterState synchronized with selectedRfqId
  useEffect(() => {
    setFilterState((prev) => ({
      ...prev,
      selectedRfqId: selectedRfqId,
    }));
  }, [selectedRfqId]);

  // Modal inspection states
  const [explainScoreBid, setExplainScoreBid] = useState<ComparisonSupplierBid | null>(null);
  const [dossierBid, setDossierBid] = useState<ComparisonSupplierBid | null>(null);
  const [isWeightsModalOpen, setIsWeightsModalOpen] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // React Query: Backend Comparison Data & Weights
  // -------------------------------------------------------------------------
  const {
    data: comparisonResponse,
    isLoading: isComparisonLoading,
    isError: isComparisonError,
    error: comparisonError,
    refetch: refetchComparison,
  } = useRfqComparison(selectedRfqId, {
    approvedOnly: filterState.approvedOnly,
  });

  const { data: weightsData } = useRfqComparisonWeights(selectedRfqId);

  const updateWeightsMutation = useUpdateComparisonWeights(selectedRfqId);
  const regenerateMutation = useRegenerateComparison(selectedRfqId);

  // Raw mock quotations fallback if needed
  const rawQuotations = useMemo(() => {
    return selectedRfq ? getQuotationsByRfq(selectedRfq.id) : [];
  }, [selectedRfq, getQuotationsByRfq]);

  // Compute all supplier bids from backend data (or fallback gracefully)
  const allBids = useMemo(() => {
    if (comparisonResponse && comparisonResponse.supplier_comparison?.length > 0) {
      return adaptBackendComparisonToBids(comparisonResponse, selectedRfq);
    }
    if (selectedRfq && rawQuotations.length > 0) {
      return buildComparisonData(selectedRfq, rawQuotations);
    }
    return [];
  }, [comparisonResponse, selectedRfq, rawQuotations]);

  // Sync visible supplier IDs when bids change or on RFQ change
  useEffect(() => {
    if (allBids.length > 0 && filterState.visibleSupplierIds.length === 0) {
      setFilterState((prev) => ({
        ...prev,
        visibleSupplierIds: allBids.map((b) => b.supplierId),
      }));
    }
  }, [allBids, filterState.visibleSupplierIds.length]);

  // Handle RFQ Selection
  const handleSelectRfq = (rfqId: string) => {
    setSelectedRfqId(rfqId);
    setSearchParams({ rfqId });
    setFilterState((prev) => ({
      ...prev,
      selectedRfqId: rfqId,
      visibleSupplierIds: [],
    }));
  };

  const handleResetFilters = () => {
    setFilterState({
      selectedRfqId: selectedRfqId,
      sortBy: 'highest_score',
      minSpecMatch: 0,
      maxLeadWeeks: 0,
      riskFilter: 'all',
      approvedOnly: true,
      visibleSupplierIds: allBids.map((b) => b.supplierId),
    });
  };

  // Filter and Sort Bids
  const filteredAndSortedBids = useMemo(() => {
    let result = allBids.filter((bid) => {
      // Visibility Filter
      if (
        filterState.visibleSupplierIds.length > 0 &&
        !filterState.visibleSupplierIds.includes(bid.supplierId)
      ) {
        return false;
      }

      // Min Spec Match
      if (filterState.minSpecMatch > 0 && bid.specMatchPercentage < filterState.minSpecMatch) {
        return false;
      }

      // Risk Profile Filter
      if (filterState.riskFilter === 'low_risk_only' && bid.riskLevel !== 'low') {
        return false;
      }

      return true;
    });

    // Sorting
    return result.sort((a, b) => {
      switch (filterState.sortBy) {
        case 'lowest_price':
          return a.totalAmount - b.totalAmount;
        case 'highest_score':
          return b.overallScore - a.overallScore;
        case 'highest_spec':
          return b.specMatchPercentage - a.specMatchPercentage;
        case 'shortest_lead':
          return a.deliveryLeadWeeks - b.deliveryLeadWeeks;
        default:
          return 0;
      }
    });
  }, [allBids, filterState]);

  // Regenerate Comparison Action
  const handleRegenerate = async () => {
    try {
      setNotification(`Regenerating comparison for ${selectedRfq?.rfqNumber || selectedRfqId} using latest approved quotation data...`);
      await regenerateMutation.mutateAsync();
      setNotification(`Comparison matrix recomputed successfully.`);
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setNotification(`Failed to regenerate comparison: ${err.message || 'Server error'}`);
    }
  };

  // Save Customizable Weights Action
  const handleSaveWeights = async (newWeights: ScoringWeightsConfig, regenerate: boolean) => {
    try {
      await updateWeightsMutation.mutateAsync({
        weights: newWeights,
        regenerate,
      });
      setNotification(`Scoring weights updated and rankings recomputed successfully.`);
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setNotification(`Failed to update weights: ${err.message || 'Server error'}`);
    }
  };

  const [isExporting, setIsExporting] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  const handleExportEvaluation = async () => {
    if (!selectedRfq) return;
    try {
      setIsExporting(true);
      setNotification(
        `Generating publication-grade Excel comparison workbook for ${selectedRfq.rfqNumber}...`
      );
      const blob = await comparisonApi.downloadRfqComparisonExcel(selectedRfq.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `QuoteFlow_Comparison_${selectedRfq.rfqNumber || selectedRfq.id}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setNotification(`Excel report successfully downloaded.`);
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setNotification(`Failed to export Excel report: ${err.message || 'Server error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportPdf = async () => {
    if (!selectedRfq) return;
    try {
      setIsExportingPdf(true);
      setNotification(
        `Generating publication-grade PDF comparison report for ${selectedRfq.rfqNumber}...`
      );
      const blob = await comparisonApi.downloadRfqComparisonPdf(selectedRfq.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `QuoteFlow_Evaluation_${selectedRfq.rfqNumber || selectedRfq.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setNotification(`PDF report successfully downloaded.`);
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setNotification(`Failed to export PDF report: ${err.message || 'Server error'}`);
    } finally {
      setIsExportingPdf(false);
    }
  };

  if (!selectedRfq || rfqs.length === 0) {
    return (
      <PageContainer>
        <div className="text-center py-24 max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-indigo-600" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">No RFQs Available for Comparison</h2>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Create an RFQ, upload vendor quotations, and run AI extraction to view side-by-side cost and specification comparisons.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link to={ROUTES.RFQ_CREATE}>
              <Button variant="primary" size="sm" leftIcon={<Plus className="w-4 h-4" />}>
                Create New RFQ
              </Button>
            </Link>
          </div>
        </div>
      </PageContainer>
    );
  }

  const unreviewedCount = comparisonResponse?.quotations_summary?.unreviewed_quotations_count || 0;

  return (
    <PageContainer>
      {/* Toast Notification */}
      {notification && (
        <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-xl text-xs font-medium flex items-center justify-between shadow-2xs animate-in fade-in">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
            <span>{notification}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-indigo-600 hover:text-indigo-900 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Header */}
      <PageHeader
        breadcrumbs={[
          { label: 'RFQs', href: ROUTES.RFQS },
          { label: selectedRfq.rfqNumber, href: `/rfqs/${selectedRfq.id}` },
          { label: 'Supplier Comparison Matrix' },
        ]}
        title={`Supplier Comparison Matrix: ${selectedRfq.rfqNumber}`}
        description={`Side-by-side commercial comparison, specification verification, and explainable scoring for ${selectedRfq.title}.`}
        actions={
          <div className="flex items-center gap-2">
            <Link to={`/rfqs/${selectedRfq.id}`}>
              <Button variant="outline" size="sm" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
                View RFQ Scope
              </Button>
            </Link>

            <Link to={`${ROUTES.REPORTS}?rfqId=${selectedRfq.id}`}>
              <Button variant="primary" size="sm" leftIcon={<FileText className="w-4 h-4" />}>
                Executive Report
              </Button>
            </Link>

            <Button
              variant="outline"
              size="sm"
              onClick={handleExportEvaluation}
              isLoading={isExporting}
              disabled={isExporting || isExportingPdf}
              leftIcon={<Download className="w-4 h-4" />}
            >
              Export Excel
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={handleExportPdf}
              isLoading={isExportingPdf}
              disabled={isExporting || isExportingPdf}
              leftIcon={<FileText className="w-4 h-4" />}
            >
              Export PDF
            </Button>
          </div>
        }
      />

      {/* Decision Support Advisory & Guardrail Banner */}
      <div className="mb-6 p-4 bg-slate-50 border border-slate-200/90 rounded-xl text-xs text-slate-700 flex items-start gap-3 shadow-2xs">
        <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed flex-1">
          <div className="flex items-center gap-2">
            <strong className="text-slate-900 font-semibold block text-xs">
              Objective Decision Support — Human Procurement Award Determination Required
            </strong>
            <DataOriginBadge type="decision" label="Human Award Gate" />
          </div>
          <span>
            QuoteFlow AI does not automatically award contracts or purchase from suppliers. This comparison screen provides transparent mathematical scoring, highlights specification mismatches, and flags commercial risks so your procurement committee can make informed award determinations.
          </span>
        </div>
      </div>

      {/* Loading or Error Banners */}
      {isComparisonLoading && (
        <div className="mb-6 p-4 bg-indigo-50/50 border border-indigo-100 rounded-xl text-xs text-indigo-900 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <RefreshCw className="w-4 h-4 text-indigo-600 animate-spin" />
            <span>Fetching live comparison snapshot from backend comparison engine...</span>
          </div>
        </div>
      )}

      {isComparisonError && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>
              Unable to load comparison from backend: {(comparisonError as any)?.message || 'Network error'}. Showing local fallback view.
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchComparison()}
            className="text-xs"
          >
            Retry
          </Button>
        </div>
      )}

      {/* 1. Comparison KPI Summary Cards */}
      <ComparisonSummaryCards
        rfq={selectedRfq}
        bids={allBids}
        priceData={comparisonResponse?.price_comparison}
        unreviewedCount={unreviewedCount}
      />

      {/* 2. Comparison Filter Bar */}
      <ComparisonFilterBar
        rfqs={rfqs}
        selectedRfqId={selectedRfqId}
        onSelectRfq={handleSelectRfq}
        filterState={filterState}
        onFilterChange={(updates) => setFilterState((prev) => ({ ...prev, ...updates }))}
        availableBids={allBids}
        onResetFilters={handleResetFilters}
        onOpenCustomWeights={() => setIsWeightsModalOpen(true)}
        onRegenerate={handleRegenerate}
        isRegenerating={regenerateMutation.isPending}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
      />

      {/* 3. Tabbed Content */}
      {activeTab === 'matrix' && (
        <ComparisonMatrixTable
          rfq={selectedRfq}
          bids={filteredAndSortedBids}
          priceData={comparisonResponse?.price_comparison}
          onOpenExplainScore={(bid) => setExplainScoreBid(bid)}
          onOpenSupplierDossier={(bid) => setDossierBid(bid)}
        />
      )}

      {activeTab === 'price' && (
        <PriceComparisonView
          rfq={selectedRfq}
          priceData={comparisonResponse?.price_comparison}
        />
      )}

      {activeTab === 'specs' && (
        <SpecsMatchingView
          rfq={selectedRfq}
          specsData={comparisonResponse?.specification_matching}
        />
      )}

      {activeTab === 'risk' && (
        <RiskFlagsView
          rfq={selectedRfq}
          riskReports={comparisonResponse?.risk_flags}
        />
      )}

      {/* Modal: Explainable Scoring Breakdown */}
      <ExplainableScoreModal
        isOpen={!!explainScoreBid}
        onClose={() => setExplainScoreBid(null)}
        selectedBid={explainScoreBid}
        allBids={allBids}
      />

      {/* Modal: Supplier Dossier & Detail View */}
      <SupplierDetailDrawer
        isOpen={!!dossierBid}
        onClose={() => setDossierBid(null)}
        bid={dossierBid}
      />

      {/* Modal: Customizable Scoring Weights */}
      <CustomWeightsModal
        isOpen={isWeightsModalOpen}
        onClose={() => setIsWeightsModalOpen(false)}
        currentWeights={weightsData?.weights}
        onSaveWeights={handleSaveWeights}
        isSaving={updateWeightsMutation.isPending}
      />
    </PageContainer>
  );
};
