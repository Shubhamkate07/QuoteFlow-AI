import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { DashboardKpiGrid } from '../../features/dashboard/components/DashboardKpiGrid';
import { RecentRfqsTable } from '../../features/dashboard/components/RecentRfqsTable';
import { RecentComparisonsCard } from '../../features/dashboard/components/RecentComparisonsCard';
import { ActivityTimeline } from '../../features/dashboard/components/ActivityTimeline';
import { CreateRfqModal } from '../../features/dashboard/components/CreateRfqModal';
import { useDashboardOverview } from '../../features/dashboard/hooks/useDashboard';
import { rfqService } from '../../features/rfq/services/rfqService';
import type { RecentRfq } from '../../features/dashboard/types';
import { ROUTES } from '../../routes/paths';
import { Plus, FileUp, Sparkles, Loader2, RefreshCw } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: dashboardData, isLoading, refetch, isFetching } = useDashboardOverview();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Live real-time data from backend API
  const metrics = dashboardData?.metrics || {
    activeRfqs: 0,
    activeRfqsChange: '0 total RFQs',
    pendingQuotes: 0,
    pendingQuotesAlertCount: 0,
    completedComparisons: 0,
    totalIdentifiedSavings: 0,
    savingsPercentage: 0,
    processingDocuments: 0,
    processingEngineStatus: 'online' as const,
  };
  const recentRfqs: RecentRfq[] = dashboardData?.recentRfqs || [];
  const recentComparisons = dashboardData?.recentComparisons || [];
  const activities = dashboardData?.activities || [];

  const handleCreateRfq = async (newRfqData: any) => {
    try {
      const created = await rfqService.createRfq({
        title: newRfqData.title || 'Untitled Custom Requisition',
        description: newRfqData.notes || '',
        currency: 'USD',
        status: 'open',
        requiredDeliveryDate: newRfqData.deadline || undefined,
        notes: newRfqData.notes || '',
      });
      setNotification(`Created requisition ${created.rfqNumber}. Redirecting to requirements...`);
      refetch();
      setTimeout(() => {
        navigate(ROUTES.RFQ_DETAIL(created.id));
      }, 1000);
    } catch (err: any) {
      console.warn('Backend RFQ creation error, opening full form:', err);
      navigate(ROUTES.RFQ_CREATE);
    }
  };

  return (
    <PageContainer>
      {/* Toast Notification */}
      {notification && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-medium flex items-center justify-between shadow-2xs animate-in fade-in">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{notification}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-emerald-600 hover:text-emerald-900 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title="Procurement Dashboard"
        description="Real-time oversight of manufacturing RFQs, unstructured quotation extraction, and supplier cost variance."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Link to={ROUTES.QUOTATIONS}>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<FileUp className="w-4 h-4 text-slate-500" />}
              >
                Quotations Workspace
              </Button>
            </Link>
            <Link to={ROUTES.RFQ_CREATE}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Plus className="w-4 h-4" />}
              >
                New RFQ
              </Button>
            </Link>
          </div>
        }
      />

      {/* Loading indicator */}
      {isLoading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-4 text-slate-500">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
          <div className="text-center">
            <h3 className="text-sm font-semibold text-slate-900">Loading Procurement Overview...</h3>
            <p className="text-xs text-slate-500 mt-1">Aggregating active RFQs, quotes, and comparison metrics</p>
          </div>
        </div>
      ) : (
        <>
          {/* 1. KPI Metric Cards */}
          <div className="mb-8">
            <DashboardKpiGrid metrics={metrics} />
          </div>

          {/* 2. Main Dashboard Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column (2 Cols on Desktop): Tables & Matrices */}
            <div className="lg:col-span-2 space-y-8">
              {/* Recent RFQs */}
              <RecentRfqsTable
                rfqs={recentRfqs}
                onCreateRfq={() => setIsCreateModalOpen(true)}
              />

              {/* Recent Supplier Comparisons */}
              <RecentComparisonsCard comparisons={recentComparisons} />
            </div>

            {/* Right Column (1 Col on Desktop): Activity & Processing Pipeline */}
            <div className="space-y-8">
              {/* Real-time Extraction Pipeline Card */}
              <Card className="p-5 border-slate-200 bg-linear-to-b from-white to-slate-50/50">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    AI Extraction Engine
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    Gemini 2.0 Flash
                  </span>
                </div>

                <div className="space-y-3">
                  <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                      <span>Multi-Format Ingestion</span>
                      <span className="text-emerald-600 font-mono text-[11px]">Active</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-emerald-500 h-full rounded-full w-full" />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>PyMuPDF & openpyxl pipeline</span>
                      <span>OCR & Formula Audit</span>
                    </div>
                  </div>

                  <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                      <span>Deterministic Validation</span>
                      <span className="text-indigo-600 font-mono text-[11px]">Enforced</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-indigo-600 h-full rounded-full w-full" />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>Tax, line totals & arithmetic checks</span>
                      <span className="text-indigo-600 font-medium">Confidence Scoring</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Audit & Activity Timeline */}
              <ActivityTimeline activities={activities} />
            </div>
          </div>
        </>
      )}

      {/* Interactive Create RFQ Modal */}
      <CreateRfqModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateRfq}
      />
    </PageContainer>
  );
};
