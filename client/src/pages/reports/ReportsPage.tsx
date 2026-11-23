import React, { useState, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { PageContainer } from '../../components/layout/PageContainer';
import { ReportHeader } from '../../features/reports/components/ReportHeader';
import { RecommendationExplanationCard } from '../../features/reports/components/RecommendationExplanationCard';
import { SupplierComparisonSummarySection } from '../../features/reports/components/SupplierComparisonSummarySection';
import { PriceSummarySection } from '../../features/reports/components/PriceSummarySection';
import { SpecificationSummarySection } from '../../features/reports/components/SpecificationSummarySection';
import { DeliverySummarySection } from '../../features/reports/components/DeliverySummarySection';
import { PaymentTermsSummarySection } from '../../features/reports/components/PaymentTermsSummarySection';
import { RiskSummarySection } from '../../features/reports/components/RiskSummarySection';
import { ScoringExplanationSection } from '../../features/reports/components/ScoringExplanationSection';
import { AuditSignOffSection } from '../../features/reports/components/AuditSignOffSection';
import { ReportExportModal } from '../../features/reports/components/ReportExportModal';
import { useRfqComparison } from '../../features/comparison/hooks/useComparison';
import { adaptBackendComparisonToBids } from '../../features/comparison/utils/comparisonScoring';
import { comparisonApi } from '../../features/comparison/api/comparisonApi';
import { useRfq } from '../../features/rfq/context/RfqContext';
import { Button } from '../../components/ui/Button';
import { ROUTES } from '../../routes/paths';
import {
  Sparkles,
  Loader2,
  AlertCircle,
  RefreshCw,
  FileSpreadsheet,
  ArrowRight,
  ShieldCheck,
  Plus,
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { rfqs, getRfqById } = useRfq();

  const queryRfqId = searchParams.get('rfqId');
  const defaultRfqId = queryRfqId || (rfqs.length > 0 ? rfqs[0].id : '');

  const [selectedRfqId, setSelectedRfqId] = useState<string>(defaultRfqId);

  // Sync selectedRfqId when query parameter changes or when rfqs load
  React.useEffect(() => {
    if (queryRfqId) {
      setSelectedRfqId(queryRfqId);
    } else if ((!selectedRfqId || selectedRfqId === 'rfq-2026-0042') && rfqs.length > 0) {
      setSelectedRfqId(rfqs[0].id);
    }
  }, [queryRfqId, rfqs, selectedRfqId]);

  const selectedRfq = getRfqById(selectedRfqId) || (rfqs.length > 0 ? rfqs[0] : undefined);

  // Fetch real comparison data from backend using React Query
  const {
    data: comparisonResponse,
    isLoading: isComparisonLoading,
    isError: isComparisonError,
    error: comparisonError,
    refetch: refetchComparison,
    isFetching: isComparisonFetching,
  } = useRfqComparison(selectedRfq?.id, { approvedOnly: true });

  // Map backend comparison data to standardized UI bids structure
  const bids = useMemo(() => {
    if (comparisonResponse && selectedRfq) {
      return adaptBackendComparisonToBids(comparisonResponse, selectedRfq);
    }
    return [];
  }, [comparisonResponse, selectedRfq]);

  // Export Modal & Direct Export State
  const [exportModal, setExportModal] = useState<{
    isOpen: boolean;
    format: 'pdf' | 'excel';
  }>({
    isOpen: false,
    format: 'pdf',
  });

  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleSelectRfq = (rfqId: string) => {
    setSelectedRfqId(rfqId);
    setSearchParams({ rfqId });
  };

  const handleTriggerExportModal = (format: 'pdf' | 'excel') => {
    setExportModal({ isOpen: true, format });
  };

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  // Direct fast download helper
  const handleDirectDownload = async (format: 'pdf' | 'excel') => {
    if (!selectedRfq) return;
    const isPdf = format === 'pdf';
    const cleanNumber = (selectedRfq.rfqNumber || selectedRfq.id).replace(/[^a-zA-Z0-9_-]/g, '_');
    const today = new Date().toISOString().split('T')[0];
    const fileName = isPdf
      ? `QuoteFlow_${cleanNumber}_Evaluation_Report_${today}.pdf`
      : `QuoteFlow_${cleanNumber}_Comparison_${today}.xlsx`;

    if (isPdf) setIsExportingPdf(true);
    else setIsExportingExcel(true);

    try {
      const blob = isPdf
        ? await comparisonApi.downloadRfqComparisonPdf(selectedRfq.id)
        : await comparisonApi.downloadRfqComparisonExcel(selectedRfq.id);

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showToast(`Successfully downloaded ${fileName}`, 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Download failed. Please check approved quotations.';
      showToast(msg, 'error');
    } finally {
      if (isPdf) setIsExportingPdf(false);
      else setIsExportingExcel(false);
    }
  };

  if (!selectedRfq || rfqs.length === 0) {
    return (
      <PageContainer>
        <div className="text-center py-24 max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-indigo-600" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">No Reports Available</h2>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Generate and export procurement evaluation reports once you have created an RFQ and uploaded supplier quotations.
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

  const hasQuotations = bids.length > 0;

  return (
    <PageContainer>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`mb-4 p-3 border rounded-xl text-xs font-medium flex items-center justify-between shadow-2xs animate-in fade-in ${
            toastMessage.type === 'error'
              ? 'bg-rose-50 border-rose-200 text-rose-800'
              : 'bg-emerald-50 border-emerald-200 text-emerald-800'
          }`}
        >
          <div className="flex items-center space-x-2">
            {toastMessage.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span>{toastMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-slate-500 hover:text-slate-800 font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* 1. Official Corporate Report Header with Export Actions & RFQ Switcher */}
      <ReportHeader
        rfqs={rfqs}
        selectedRfq={selectedRfq}
        onSelectRfq={handleSelectRfq}
        onTriggerExport={handleDirectDownload}
        onOpenExportModal={handleTriggerExportModal}
        isExportingExcel={isExportingExcel}
        isExportingPdf={isExportingPdf}
      />

      {/* Loading State */}
      {isComparisonLoading && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-12 text-center my-6 space-y-4">
          <div className="w-12 h-12 bg-indigo-50 border border-indigo-100 rounded-2xl flex items-center justify-center mx-auto">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-900">Synthesizing Comprehensive Evaluation Report</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Executing deterministic pricing analysis, specification parameter compliance, multi-factor risk flags, and scoring models...
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
            <span>RFQ: {selectedRfq.rfqNumber}</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {!isComparisonLoading && isComparisonError && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 my-6 text-xs text-rose-900 space-y-3">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <h3 className="font-bold text-sm">Failed to Load Evaluation Report Data</h3>
          </div>
          <p className="text-rose-700">
            {(comparisonError as any)?.response?.data?.error ||
              (comparisonError as any)?.message ||
              'Could not connect to the comparison engine. Please verify the backend service is running.'}
          </p>
          <div className="pt-2 flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchComparison()}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isComparisonFetching ? 'animate-spin' : ''}`} />}
              className="bg-white text-rose-800 border-rose-300 hover:bg-rose-100"
            >
              Retry Loading Report
            </Button>
            <Link
              to={`/comparisons?rfqId=${selectedRfq.id}`}
              className="text-rose-700 hover:underline flex items-center gap-1 font-semibold"
            >
              <span>Go to Comparison Matrix</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

      {/* Empty State: No Approved Quotations Compared */}
      {!isComparisonLoading && !isComparisonError && !hasQuotations && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-10 text-center my-6 space-y-4">
          <div className="w-12 h-12 bg-amber-50 border border-amber-200 rounded-2xl flex items-center justify-center mx-auto text-amber-600">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-900">No Approved Quotations Compared Yet</h3>
            <p className="text-xs text-slate-500 max-w-lg mx-auto leading-relaxed">
              Formal evaluation reports require at least one approved supplier quotation for{' '}
              <strong className="text-slate-700 font-mono">{selectedRfq.rfqNumber}</strong>. Quotations must be reviewed
              and approved in the Quotation Ingestion module or compared without filter restrictions.
            </p>
          </div>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Link to="/quotations">
              <Button variant="outline" size="sm" className="text-xs">
                Review & Approve Quotations
              </Button>
            </Link>
            <Link to={`/comparisons?rfqId=${selectedRfq.id}`}>
              <Button variant="primary" size="sm" className="text-xs bg-indigo-600 hover:bg-indigo-700" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                Open Comparison Matrix
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Populated Report Sections */}
      {!isComparisonLoading && !isComparisonError && hasQuotations && (
        <div className="space-y-6">
          {/* 2. Executive Recommendation Explanation & Tradeoff Rationale */}
          <RecommendationExplanationCard
            bids={bids}
            currency={selectedRfq.currency}
          />

          {/* 3. Executive Supplier Scorecard Summary Table */}
          <SupplierComparisonSummarySection
            bids={bids}
            currency={selectedRfq.currency}
          />

          {/* 4. Commercial Price Summary & Cost Savings Analysis */}
          <PriceSummarySection
            rfq={selectedRfq}
            bids={bids}
            currency={selectedRfq.currency}
            priceComparison={comparisonResponse?.price_comparison}
          />

          {/* 5. Technical Specification & Quality Compliance */}
          <SpecificationSummarySection
            rfq={selectedRfq}
            bids={bids}
            specMatching={comparisonResponse?.specification_matching}
          />

          {/* 6. Delivery Timeline & Logistics Summary */}
          <DeliverySummarySection
            rfq={selectedRfq}
            bids={bids}
          />

          {/* 7. Commercial Payment Terms & Warranty Analysis */}
          <PaymentTermsSummarySection
            bids={bids}
          />

          {/* 8. Multi-Factor Risk Assessment & Mitigation Matrix */}
          <RiskSummarySection
            bids={bids}
            riskReports={comparisonResponse?.risk_flags}
          />

          {/* 9. Explainable Supplier Scoring Engine & Factor Breakdown */}
          <ScoringExplanationSection
            scoring={comparisonResponse?.scoring}
          />

          {/* 10. Governance Approval & Audit Sign-off Block */}
          <AuditSignOffSection
            rfqNumber={selectedRfq.rfqNumber}
          />
        </div>
      )}

      {/* Publication Deliverable Export Modal (PDF / Excel) */}
      <ReportExportModal
        isOpen={exportModal.isOpen}
        onClose={() => setExportModal((prev) => ({ ...prev, isOpen: false }))}
        format={exportModal.format}
        rfqId={selectedRfq.id}
        rfqNumber={selectedRfq.rfqNumber}
        onSuccess={(msg) => showToast(msg, 'success')}
        onError={(err) => showToast(err, 'error')}
      />
    </PageContainer>
  );
};
