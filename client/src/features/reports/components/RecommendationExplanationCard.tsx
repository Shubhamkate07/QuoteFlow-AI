import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../../comparison/types';
import { formatCurrency } from '../../../utils/formatters';
import {
  Sparkles,
  Award,
  TrendingDown,
  AlertTriangle,
  Info,
} from 'lucide-react';

interface RecommendationExplanationCardProps {
  bids: ComparisonSupplierBid[];
  currency: string;
}

export const RecommendationExplanationCard: React.FC<RecommendationExplanationCardProps> = ({
  bids,
  currency,
}) => {
  if (bids.length === 0) return null;

  const topRankedBid = [...bids].sort((a, b) => b.overallScore - a.overallScore)[0];
  const lowestPriceBid = [...bids].sort((a, b) => a.totalAmount - b.totalAmount)[0];
  const flaggedBid =
    bids.find((b) => (b.riskFlags && b.riskFlags.length > 0) || b.materialDeviations?.length > 0) ||
    bids[bids.length - 1];

  const priceDiff = Math.abs(topRankedBid.totalAmount - lowestPriceBid.totalAmount);
  const isSameTopAndLowest = topRankedBid.supplierId === lowestPriceBid.supplierId;

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <CardTitle>Executive Recommendation & Sourcing Trade-Off Rationale</CardTitle>
              <span className="text-[11px] text-slate-500">
                Transparent multi-criteria trade-off synthesis based on price, technical specifications, delivery timeline, and commercial risk
              </span>
            </div>
          </div>

          <Badge variant="neutral" size="sm">
            Explainable Multi-Criteria Scoring
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Recommendation Cards: Primary vs Secondary Cost vs Flagged */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 1. Primary Recommended Option */}
          <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 space-y-2 relative">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Award className="w-3 h-3 text-emerald-600" />
                Top-Ranked Supplier
              </span>
              <span className="font-mono text-xs font-bold text-slate-900">
                Rank #{topRankedBid.rank}
              </span>
            </div>

            <h4 className="font-bold text-sm text-slate-900 leading-tight">
              {topRankedBid.supplierName}
            </h4>

            <div className="font-mono text-base font-extrabold text-emerald-700">
              {formatCurrency(topRankedBid.totalAmount, currency)}
            </div>

            <p className="text-[11px] text-slate-600 leading-relaxed">
              <strong>Best Overall Composite Score:</strong> Scored{' '}
              <strong className="text-slate-900">{topRankedBid.overallScore}/100</strong>. Achieves{' '}
              <strong>{topRankedBid.specMatchPercentage}%</strong> specification compliance, a{' '}
              <strong>{topRankedBid.deliveryLeadWeeks}-week</strong> lead time, favorable{' '}
              <strong>{topRankedBid.paymentTerms}</strong> terms, and a{' '}
              <strong className="capitalize">{topRankedBid.riskLevel}</strong> commercial risk rating.
            </p>
          </div>

          {/* 2. Secondary Cost-Optimization Alternative */}
          <div className="p-4 rounded-xl border border-sky-200 bg-sky-50/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 bg-sky-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                <TrendingDown className="w-3 h-3 text-sky-600" />
                Cost-Optimization Option
              </span>
              <span className="font-mono text-xs font-bold text-slate-900">
                Rank #{lowestPriceBid.rank}
              </span>
            </div>

            <h4 className="font-bold text-sm text-slate-900 leading-tight">
              {lowestPriceBid.supplierName}
            </h4>

            <div className="font-mono text-base font-extrabold text-sky-800">
              {formatCurrency(lowestPriceBid.totalAmount, currency)}
            </div>

            <p className="text-[11px] text-slate-600 leading-relaxed">
              {isSameTopAndLowest ? (
                <span>
                  <strong>Lowest Cost & Top Rated:</strong> This proposal represents both the lowest quoted price and the highest overall evaluation score.
                </span>
              ) : (
                <span>
                  <strong>Lowest Cost Baseline:</strong> Saves{' '}
                  <strong className="text-emerald-700 font-mono">
                    {formatCurrency(priceDiff, currency)}
                  </strong>{' '}
                  compared to the top-ranked bidder, with {lowestPriceBid.specMatchPercentage}% specification match and {lowestPriceBid.deliveryLeadWeeks}-week delivery.
                </span>
              )}
            </p>
          </div>

          {/* 3. Risk Warning / Exception Review */}
          <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-600" />
                Risk / Exception Review
              </span>
              <span className="font-mono text-xs font-bold text-slate-900">
                Rank #{flaggedBid.rank}
              </span>
            </div>

            <h4 className="font-bold text-sm text-slate-900 leading-tight">
              {flaggedBid.supplierName}
            </h4>

            <div className="font-mono text-base font-extrabold text-slate-900">
              {formatCurrency(flaggedBid.totalAmount, currency)}
            </div>

            <p className="text-[11px] text-slate-600 leading-relaxed">
              {flaggedBid.riskFlags && flaggedBid.riskFlags.length > 0 ? (
                <span>
                  <strong>Rule Exceptions Flagged:</strong> Identified {flaggedBid.riskFlags.length} risk items ({flaggedBid.riskFlagDetails?.[0]?.title || flaggedBid.riskFlags[0]}). Requires review before contracting.
                </span>
              ) : (
                <span>
                  <strong>Commercial Review:</strong> Specification compliance at {flaggedBid.specMatchPercentage}%, lead time of {flaggedBid.deliveryLeadWeeks} weeks.
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Explainable Decision Support Guidance Note */}
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start gap-2.5 text-xs text-slate-600">
          <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="text-slate-900">Human Procurement Authority Notice:</strong> QuoteFlow AI
            delivers explainable decision-support recommendations based on deterministic data calculations and rule-based risk checks. The system does not execute automated purchase orders or contracts.
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
