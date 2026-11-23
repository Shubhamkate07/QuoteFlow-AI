import React from 'react';
import { Card, CardContent } from '../../../components/ui/Card';
import { formatCurrency } from '../../../utils/formatters';
import type { ComparisonSupplierBid, BackendPriceComparisonData } from '../types';
import type { Rfq } from '../../rfq/types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  DollarSign,
  TrendingDown,
  Award,
  ShieldCheck,
  AlertTriangle,
  Split,
} from 'lucide-react';

interface ComparisonSummaryCardsProps {
  rfq: Rfq;
  bids: ComparisonSupplierBid[];
  priceData?: BackendPriceComparisonData;
  unreviewedCount?: number;
}

export const ComparisonSummaryCards: React.FC<ComparisonSummaryCardsProps> = ({
  rfq,
  bids,
  priceData,
  unreviewedCount = 0,
}) => {
  if (bids.length === 0) return null;

  const lowestBid = [...bids].sort((a, b) => a.totalAmount - b.totalAmount)[0];
  const topScoringBid = [...bids].sort((a, b) => b.overallScore - a.overallScore)[0];

  const targetBudget =
    rfq.targetBudget && rfq.targetBudget > 0
      ? rfq.targetBudget
      : (rfq.items || []).reduce((sum, item) => sum + (item.quantity || 0) * (item.targetUnitPrice || 0), 0) ||
        (lowestBid ? lowestBid.totalAmount : 0);
  const totalSavings = targetBudget > 0 ? targetBudget - lowestBid.totalAmount : 0;
  const savingsPct =
    targetBudget > 0 ? Math.round((totalSavings / targetBudget) * 1000) / 10 : 0;

  const currency = lowestBid?.currency || rfq.currency || 'USD';
  const cherryPickSavings = priceData?.cherry_pick_savings || 0;
  const cherryPickTotal = priceData?.cherry_pick_total || 0;

  return (
    <div className="space-y-4 mb-6">
      {/* Notice for unreviewed quotations */}
      {unreviewedCount > 0 && (
        <div className="p-3.5 bg-amber-50/90 border border-amber-300 rounded-xl text-xs text-amber-900 flex items-start gap-2.5 shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="leading-relaxed flex-1">
            <div className="flex items-center gap-2">
              <strong className="font-semibold text-amber-950 block text-xs">
                {unreviewedCount} Quotation{unreviewedCount === 1 ? '' : 's'} Pending Human Review
              </strong>
              <DataOriginBadge type="decision" label="Review Gate" />
            </div>
            <span>
              Unreviewed or pending AI extractions are currently excluded from official scoring to prevent unverified data from influencing procurement comparisons. To compare all submitted quotes, verify and approve them in the Quotation Review module.
            </span>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Target Baseline Budget */}
        <Card className="hover:border-slate-300 transition-colors">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-1.5 mb-1">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Target Baseline Budget
                </span>
                <DataOriginBadge type="extracted" size="xs" />
              </div>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">
                {formatCurrency(targetBudget, currency)}
              </div>
              <span className="text-[11px] text-slate-400 mt-0.5 block">
                Approved procurement ceiling
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
              <DollarSign className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* 2. Lowest Total Quoted Bid */}
        <Card className="hover:border-slate-300 transition-colors border-emerald-200/80 bg-emerald-50/10">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-1.5 mb-1">
                <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
                  Lowest Quoted Bid
                </span>
                <DataOriginBadge type="calculated" size="xs" />
              </div>
              <div className="text-2xl font-bold text-emerald-700 mt-1 font-mono">
                {formatCurrency(lowestBid.totalAmount, currency)}
              </div>
              <span className="text-[11px] text-emerald-700/80 mt-0.5 flex items-center gap-1 font-medium">
                <TrendingDown className="w-3.5 h-3.5" />
                {totalSavings > 0
                  ? `Saves ${formatCurrency(totalSavings, currency)} (${savingsPct}%)`
                  : 'Meets target budget'}
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Award className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* 3. Cherry-Pick Optimal Allocation */}
        <Card className="hover:border-slate-300 transition-colors border-purple-200/80 bg-purple-50/10">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-1.5 mb-1">
                <span className="text-[11px] font-semibold text-purple-700 uppercase tracking-wider">
                  Cherry-Pick Optimal
                </span>
                <DataOriginBadge type="calculated" size="xs" />
              </div>
              <div className="text-2xl font-bold text-purple-950 mt-1 font-mono">
                {cherryPickTotal > 0
                  ? formatCurrency(cherryPickTotal, currency)
                  : formatCurrency(lowestBid.totalAmount, currency)}
              </div>
              <span className="text-[11px] text-purple-700/80 mt-0.5 flex items-center gap-1 font-medium">
                <Split className="w-3.5 h-3.5" />
                {cherryPickSavings > 0
                  ? `Extra ${formatCurrency(cherryPickSavings, currency)} savings`
                  : 'Best item-by-item split'}
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Split className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* 4. Top Ranked Option */}
        <Card className="hover:border-slate-300 transition-colors border-indigo-200/80 bg-indigo-50/10">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-1.5 mb-1">
                <span className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wider block">
                  Top Ranked Option
                </span>
                <DataOriginBadge type="decision" size="xs" label="Weighted" />
              </div>
              <div className="text-2xl font-bold text-indigo-950 mt-1 flex items-baseline gap-1.5 font-mono">
                <span>{topScoringBid.overallScore}</span>
                <span className="text-xs text-slate-400 font-normal">/ 100</span>
              </div>
              <span
                className="text-[11px] text-indigo-700 truncate max-w-[160px] block mt-0.5 font-medium"
                title={topScoringBid.supplierName}
              >
                {topScoringBid.supplierName}
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
