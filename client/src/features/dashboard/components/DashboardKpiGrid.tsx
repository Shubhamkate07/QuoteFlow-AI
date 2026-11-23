import React from 'react';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import {
  FileSpreadsheet,
  Clock,
  CheckCircle2,
  Cpu,
  TrendingDown,
} from 'lucide-react';
import { formatCurrency } from '../../../utils/formatters';
import type { DashboardMetrics } from '../types';

interface DashboardKpiGridProps {
  metrics: DashboardMetrics;
}

export const DashboardKpiGrid: React.FC<DashboardKpiGridProps> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Active RFQs */}
      <Card className="p-5 hover:border-slate-300 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Active RFQs
          </span>
          <div className="p-2 rounded-lg bg-slate-100 text-slate-700">
            <FileSpreadsheet className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-bold text-slate-900">{metrics.activeRfqs}</div>
          <Badge variant="neutral" size="sm" className="font-semibold text-[10px]">
            {metrics.activeRfqsChange}
          </Badge>
        </div>
        <div className="mt-2 text-xs text-slate-500 flex items-center">
          <span>In active bidding or review stage</span>
        </div>
      </Card>

      {/* 2. Pending Quotations */}
      <Card className="p-5 hover:border-slate-300 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Pending Quotations
          </span>
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-bold text-slate-900">{metrics.pendingQuotes}</div>
          {metrics.pendingQuotesAlertCount > 0 && (
            <Badge variant="warning" dot size="sm" className="font-semibold text-[10px]">
              {metrics.pendingQuotesAlertCount} Need Review
            </Badge>
          )}
        </div>
        <div className="mt-2 text-xs text-slate-500">
          Awaiting human verification or spec match
        </div>
      </Card>

      {/* 3. Comparisons Completed */}
      <Card className="p-5 hover:border-slate-300 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Comparisons Completed
          </span>
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-bold text-slate-900">{metrics.completedComparisons}</div>
          <span className="text-xs font-semibold text-emerald-700 flex items-center gap-0.5">
            <TrendingDown className="w-3.5 h-3.5" />
            {metrics.savingsPercentage}% avg
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-600 font-medium flex items-center justify-between">
          <span>Identified Savings:</span>
          <span className="text-emerald-700 font-bold">
            {formatCurrency(metrics.totalIdentifiedSavings)}
          </span>
        </div>
      </Card>

      {/* 4. Documents Currently Processing */}
      <Card className="p-5 hover:border-slate-300 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            In Processing Queue
          </span>
          <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
            <Cpu className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <span>{metrics.processingDocuments}</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          </div>
          <Badge variant="primary" size="sm" className="font-semibold text-[10px]">
            Gemini 2.0 Parser
          </Badge>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          Extracting tabular specs & unit costs
        </div>
      </Card>
    </div>
  );
};
