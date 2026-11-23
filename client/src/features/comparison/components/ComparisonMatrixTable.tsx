import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid, BackendPriceComparisonData } from '../types';
import type { Rfq } from '../../rfq/types';
import { formatCurrency } from '../../../utils/formatters';
import { ROUTES } from '../../../routes/paths';
import { DataOriginBadge } from './DataOriginBadge';
import {
  Sparkles,
  TrendingDown,
  CheckCircle2,
  AlertTriangle,
  Eye,
  FileSearch,
  Award,
  Layers,
  Truck,
  CreditCard,
  ShieldCheck,
} from 'lucide-react';

interface ComparisonMatrixTableProps {
  rfq: Rfq;
  bids: ComparisonSupplierBid[];
  priceData?: BackendPriceComparisonData;
  onOpenExplainScore: (bid: ComparisonSupplierBid) => void;
  onOpenSupplierDossier: (bid: ComparisonSupplierBid) => void;
}

export const ComparisonMatrixTable: React.FC<ComparisonMatrixTableProps> = ({
  rfq,
  bids,
  priceData: _priceData,
  onOpenExplainScore,
  onOpenSupplierDossier,
}) => {
  if (bids.length === 0) {
    return (
      <Card className="p-12 text-center text-slate-500">
        <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-800">No Bids Match Current Filters</h4>
        <p className="text-xs text-slate-400 mt-1">
          Adjust the minimum specification match, risk profile, or supplier visibility settings above.
        </p>
      </Card>
    );
  }

  const currency = bids[0]?.currency || rfq.currency || 'USD';
  const targetBudget =
    rfq.targetBudget && rfq.targetBudget > 0
      ? rfq.targetBudget
      : (rfq.items || []).reduce((sum, item) => sum + (item.quantity || 0) * (item.targetUnitPrice || 0), 0);

  return (
    <Card className="overflow-hidden border border-slate-200 shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          {/* Header Row: Suppliers */}
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {/* Sticky Parameter Column */}
              <th className="py-4 px-4 w-72 min-w-[280px] bg-slate-50/95 border-r border-slate-200 align-top">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Procurement Metric
                </span>
                <span className="text-xs font-semibold text-slate-900 mt-0.5 block">
                  {rfq.rfqNumber}: {rfq.title}
                </span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] text-slate-500 font-mono">
                    Baseline Cap: {formatCurrency(targetBudget, currency)}
                  </span>
                  <DataOriginBadge type="extracted" size="xs" />
                </div>
              </th>

              {/* Dynamic Supplier Columns */}
              {bids.map((bid) => (
                <th
                  key={bid.quotationId}
                  className={`py-4 px-4 min-w-[280px] align-top border-r border-slate-200 last:border-r-0 transition-colors ${
                    bid.rank === 1 ? 'bg-indigo-50/25' : 'bg-slate-50'
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                            bid.rank === 1
                              ? 'bg-indigo-600 text-white'
                              : bid.rank === 2
                              ? 'bg-slate-200 text-slate-800'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          Rank #{bid.rank}
                        </span>
                        {bid.isApproved ? (
                          <Badge variant="success" size="sm" className="text-[9px] py-0 px-1.5">
                            Verified
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm" className="text-[9px] py-0 px-1.5">
                            Pending Review
                          </Badge>
                        )}
                      </div>

                      {bid.recommendationTag && (
                        <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded">
                          {bid.recommendationTag}
                        </span>
                      )}
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 leading-tight">
                      {bid.supplierName}
                    </h4>

                    <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                      <span>Ref: {bid.quoteReference}</span>
                      <span>•</span>
                      <span>{bid.fileName}</span>
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {/* SECTION 1: EXPLAINABLE SCORING */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>1. Multi-Criteria Scoring & Evaluated Rank</span>
                <div className="flex items-center gap-1.5">
                  <DataOriginBadge type="calculated" size="xs" label="Formulas" />
                  <DataOriginBadge type="decision" size="xs" label="Custom Weights" />
                </div>
              </td>
            </tr>

            {/* Overall Score Row */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3.5 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">Overall Evaluated Score</div>
                  <DataOriginBadge type="calculated" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Formula: Price 40% + Specs 30% + Delivery 15% + Terms 10% + Warranty 5%
                </div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3.5 px-4 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-baseline space-x-1.5">
                      <span className="text-2xl font-black font-mono text-slate-900">
                        {bid.overallScore}
                      </span>
                      <span className="text-xs text-slate-400 font-normal">/ 100</span>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onOpenExplainScore(bid)}
                      className="text-xs text-indigo-600 hover:bg-indigo-50 px-2 py-1 h-auto"
                      leftIcon={<Sparkles className="w-3.5 h-3.5 text-indigo-500" />}
                    >
                      Explain Score
                    </Button>
                  </div>

                  {/* Factor Score Mini Pills */}
                  <div className="grid grid-cols-5 gap-1 mt-2 text-center text-[10px] font-mono">
                    <div className="p-1 rounded bg-slate-100/70 border border-slate-200/60" title="Price Score">
                      <span className="text-[9px] text-slate-400 block">Price</span>
                      <span className="font-bold text-slate-800">
                        {bid.scoreBreakdown.find((f) => f.id === 'price')?.weightedScore || 0}
                      </span>
                    </div>
                    <div className="p-1 rounded bg-slate-100/70 border border-slate-200/60" title="Specs Score">
                      <span className="text-[9px] text-slate-400 block">Spec</span>
                      <span className="font-bold text-slate-800">
                        {bid.scoreBreakdown.find((f) => f.id === 'spec_match')?.weightedScore || 0}
                      </span>
                    </div>
                    <div className="p-1 rounded bg-slate-100/70 border border-slate-200/60" title="Delivery Score">
                      <span className="text-[9px] text-slate-400 block">Del</span>
                      <span className="font-bold text-slate-800">
                        {bid.scoreBreakdown.find((f) => f.id === 'delivery')?.weightedScore || 0}
                      </span>
                    </div>
                    <div className="p-1 rounded bg-slate-100/70 border border-slate-200/60" title="Terms Score">
                      <span className="text-[9px] text-slate-400 block">Term</span>
                      <span className="font-bold text-slate-800">
                        {bid.scoreBreakdown.find((f) => f.id === 'payment_terms')?.weightedScore || 0}
                      </span>
                    </div>
                    <div className="p-1 rounded bg-slate-100/70 border border-slate-200/60" title="Warranty Score">
                      <span className="text-[9px] text-slate-400 block">War</span>
                      <span className="font-bold text-slate-800">
                        {bid.scoreBreakdown.find((f) => f.id === 'warranty')?.weightedScore || 0}
                      </span>
                    </div>
                  </div>
                </td>
              ))}
            </tr>

            {/* SECTION 2: COMMERCIAL & FINANCIAL */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>2. Commercial & Price Comparison</span>
                <div className="flex items-center gap-1.5">
                  <DataOriginBadge type="extracted" size="xs" label="Quoted Totals" />
                  <DataOriginBadge type="calculated" size="xs" label="Variance & Subtotals" />
                </div>
              </td>
            </tr>

            {/* Grand Total Quoted Amount */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3.5 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">Total Quoted Amount</div>
                  <DataOriginBadge type="extracted" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Target: {formatCurrency(targetBudget, currency)}
                </div>
              </td>
              {bids.map((bid) => (
                <td
                  key={bid.quotationId}
                  className={`py-3.5 px-4 border-r border-slate-200 last:border-r-0 ${
                    bid.isLowestTotalAmount ? 'bg-emerald-50/20' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-lg font-mono font-extrabold ${
                        bid.isLowestTotalAmount ? 'text-emerald-700' : 'text-slate-900'
                      }`}
                    >
                      {formatCurrency(bid.totalAmount, bid.currency)}
                    </span>

                    {/* Lowest Price Highlight Badge */}
                    {bid.isLowestTotalAmount && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px] border border-emerald-300">
                        <Award className="w-3 h-3 text-emerald-600" />
                        Lowest Price
                      </span>
                    )}
                  </div>

                  {/* Calculated Variance vs Target Budget */}
                  <div className="mt-1 text-[11px] font-mono flex items-center space-x-1">
                    {targetBudget > 0 ? (
                      bid.varianceVsBudget < 0 ? (
                        <span className="text-emerald-700 font-semibold flex items-center gap-0.5">
                          <TrendingDown className="w-3 h-3" />
                          Saves {formatCurrency(Math.abs(bid.varianceVsBudget), bid.currency)} (
                          {Math.abs(bid.variancePercentage)}%)
                        </span>
                      ) : bid.varianceVsBudget > 0 ? (
                        <span className="text-rose-600 font-semibold">
                          +{formatCurrency(bid.varianceVsBudget, bid.currency)} (+
                          {bid.variancePercentage}%) over budget
                        </span>
                      ) : (
                        <span className="text-slate-600 font-semibold">
                          Meets baseline budget exact ({formatCurrency(targetBudget, currency)})
                        </span>
                      )
                    ) : (
                      <span className="text-slate-400 font-normal">
                        No target budget configured
                      </span>
                    )}
                  </div>
                </td>
              ))}
            </tr>

            {/* Subtotal, Taxes & Shipping Breakdown */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-2.5 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <span className="text-slate-900 font-semibold">Subtotal / Tax / Shipping</span>
                  <DataOriginBadge type="calculated" size="xs" />
                </div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-2.5 px-4 text-xs font-mono text-slate-700 border-r border-slate-200 last:border-r-0">
                  <div className="space-y-0.5 text-[11px]">
                    <div>Subtotal: {bid.subtotal != null ? formatCurrency(bid.subtotal, bid.currency) : '—'}</div>
                    <div className="text-slate-500">Tax: {bid.taxAmount != null ? formatCurrency(bid.taxAmount, bid.currency) : '0'}</div>
                    <div className="text-slate-500">Shipping: {bid.shippingAmount != null ? formatCurrency(bid.shippingAmount, bid.currency) : '0'}</div>
                  </div>
                </td>
              ))}
            </tr>

            {/* SECTION 3: DELIVERY & LOGISTICS */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>3. Delivery Lead Time & Milestones</span>
                <div className="flex items-center gap-1.5">
                  <DataOriginBadge type="extracted" size="xs" label="Quoted Lead Weeks" />
                  <DataOriginBadge type="calculated" size="xs" label="On-Time Status" />
                </div>
              </td>
            </tr>

            {/* Lead Time Row */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">Delivery Lead Time</div>
                  <DataOriginBadge type="extracted" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Required Date: {rfq.requiredDeliveryDate || 'Standard Schedule'}</div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3 px-4 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1.5 font-semibold text-xs text-slate-900">
                      <Truck className="w-3.5 h-3.5 text-slate-400" />
                      <span>{bid.deliveryLeadWeeks} Calendar Weeks</span>
                    </div>

                    {bid.isShortestLeadTime && (
                      <span className="text-[10px] font-bold text-sky-700 bg-sky-50 border border-sky-200 px-1.5 py-0.2 rounded">
                        Fastest
                      </span>
                    )}
                  </div>

                  <div className="mt-1">
                    {bid.onTimeStatus === 'On Schedule' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-semibold">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Fulfills Schedule
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 font-semibold">
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        Delivery Delay Risk
                      </span>
                    )}
                  </div>
                </td>
              ))}
            </tr>

            {/* SECTION 4: PAYMENT TERMS & CASH FLOW */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>4. Payment Terms & Commercial Risk</span>
                <DataOriginBadge type="extracted" size="xs" label="Quoted Terms" />
              </td>
            </tr>

            {/* Payment Terms Row */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900">Commercial Terms</span>
                  <DataOriginBadge type="extracted" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Credit line & deposit terms</div>
              </td>
              {bids.map((bid) => {
                const isAdvance =
                  bid.paymentTerms.toLowerCase().includes('advance') ||
                  bid.paymentTerms.toLowerCase().includes('deposit');
                return (
                  <td key={bid.quotationId} className="py-3 px-4 border-r border-slate-200 last:border-r-0">
                    <div className="flex items-center space-x-2">
                      <CreditCard className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span
                        className={`text-xs ${
                          isAdvance ? 'font-bold text-amber-800' : 'font-semibold text-slate-900'
                        }`}
                      >
                        {bid.paymentTerms}
                      </span>
                    </div>
                    {isAdvance && (
                      <span className="block mt-1 text-[10px] text-amber-700 font-medium">
                        ⚠ Advance deposit required
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>

            {/* Warranty & Guarantee */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900">Warranty Coverage</span>
                  <DataOriginBadge type="extracted" size="xs" />
                </div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3 px-4 text-xs text-slate-800 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center space-x-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{bid.warrantyTerms || '12 Months Standard'}</span>
                  </div>
                </td>
              ))}
            </tr>

            {/* SECTION 5: COMPLIANCE & SPECIFICATION MATCHING */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>5. Technical Specification Compliance & Risk Flags</span>
                <div className="flex items-center gap-1.5">
                  <DataOriginBadge type="ai" size="xs" label="AI Match" />
                  <DataOriginBadge type="risk" size="xs" label="Rule Flags" />
                </div>
              </td>
            </tr>

            {/* Spec Match Row */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3.5 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">Specification Compliance</div>
                  <DataOriginBadge type="ai" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Tolerance & material compliance</div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3.5 px-4 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-bold text-slate-900">
                      {bid.specMatchPercentage}% Match
                    </span>

                    {bid.specMatchPercentage === 100 ? (
                      <Badge variant="success" size="sm">
                        Verified
                      </Badge>
                    ) : (
                      <Badge variant="warning" size="sm">
                        Variance
                      </Badge>
                    )}
                  </div>

                  <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        bid.specMatchPercentage === 100
                          ? 'bg-emerald-500'
                          : bid.specMatchPercentage >= 90
                          ? 'bg-sky-500'
                          : 'bg-amber-500'
                      }`}
                      style={{ width: `${bid.specMatchPercentage}%` }}
                    />
                  </div>

                  {bid.materialDeviations.length > 0 && (
                    <div className="mt-2 p-2 bg-amber-50 rounded border border-amber-200 text-[10px] text-amber-900 font-medium">
                      <div className="flex items-start gap-1">
                        <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
                        <span>⚠ Mismatch: {bid.materialDeviations.join('; ')}</span>
                      </div>
                    </div>
                  )}
                </td>
              ))}
            </tr>

            {/* Risk Assessment Flags */}
            <tr className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3.5 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">Risk Assessment Flags</div>
                  <DataOriginBadge type="risk" size="xs" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Deterministic 14-rule risk audit</div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3.5 px-4 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center space-x-2 mb-1.5">
                    <span
                      className={`text-[10px] font-bold uppercase font-mono px-2 py-0.5 rounded ${
                        bid.riskLevel === 'low'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : bid.riskLevel === 'medium'
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}
                    >
                      {bid.riskLevel} Risk
                    </span>
                    <span className="text-[10px] text-slate-400">
                      ({bid.riskFlags.length} Flag{bid.riskFlags.length === 1 ? '' : 's'})
                    </span>
                  </div>

                  {bid.riskFlags.length > 0 ? (
                    <div className="space-y-1">
                      {bid.riskFlags.map((risk, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-1 text-[10px] text-slate-600 bg-slate-50 p-1.5 rounded border border-slate-100"
                        >
                          <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
                          <span>{risk}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1.5 text-[11px] text-emerald-700 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Zero audit risk flags detected</span>
                    </div>
                  )}
                </td>
              ))}
            </tr>

            {/* SECTION 6: BOM LINE ITEMS SCHEDULE */}
            <tr className="bg-slate-50/80 font-semibold text-slate-700 text-[11px]">
              <td colSpan={bids.length + 1} className="py-2 px-4 uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>6. BOM Line Items Unit Prices & Optimal Sourcing</span>
                <div className="flex items-center gap-1.5">
                  <DataOriginBadge type="extracted" size="xs" label="Unit Price" />
                  <DataOriginBadge type="calculated" size="xs" label="Extended Total" />
                </div>
              </td>
            </tr>

            {/* RFQ Items Rows */}
            {rfq.items && rfq.items.length > 0 ? (
              rfq.items.map((rfqItem) => (
                <tr key={rfqItem.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="py-3 px-4 font-medium text-slate-700 bg-slate-50/40 border-r border-slate-200 max-w-xs">
                    <div className="font-semibold text-slate-900">{rfqItem.name}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      Target: {formatCurrency(rfqItem.targetUnitPrice || 0, currency)} / {rfqItem.unit} • Qty: {(rfqItem.quantity ?? 0).toLocaleString()} {rfqItem.unit}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate" title={rfqItem.requiredSpecifications}>
                      {rfqItem.requiredSpecifications}
                    </div>
                  </td>

                  {bids.map((bid) => {
                    const lineItem = bid.lineItemsMap[rfqItem.id];

                    if (!lineItem) {
                      return (
                        <td key={bid.quotationId} className="py-3 px-4 text-slate-400 italic text-[11px] border-r border-slate-200 last:border-r-0">
                          Not quoted in document
                        </td>
                      );
                    }

                    return (
                      <td
                        key={bid.quotationId}
                        className={`py-3 px-4 border-r border-slate-200 last:border-r-0 ${
                          lineItem.isLowestUnitPrice ? 'bg-emerald-50/15' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="font-mono font-bold text-slate-900 text-xs">
                            {formatCurrency(lineItem.unitPrice, bid.currency)}
                            <span className="text-[10px] font-normal text-slate-400 ml-1">/ unit</span>
                          </div>

                          {lineItem.isLowestUnitPrice && (
                            <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 text-[9px] font-bold">
                              Lowest
                            </span>
                          )}
                        </div>

                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          Ext: {formatCurrency(lineItem.totalPrice, bid.currency)}
                        </div>

                        <div className="mt-1 text-[10px] text-slate-600">
                          {lineItem.hasVariance ? (
                            <div className="p-1 bg-amber-50 rounded border border-amber-200 text-amber-800 font-semibold">
                              ⚠ {lineItem.discrepancyNote || lineItem.materialSpec}
                            </div>
                          ) : (
                            <span className="truncate block font-mono text-[10px]" title={lineItem.materialSpec}>
                              {lineItem.materialSpec}
                            </span>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={bids.length + 1} className="py-4 px-4 text-center text-slate-400 italic">
                  No line items configured for this RFQ.
                </td>
              </tr>
            )}

            {/* SECTION 7: ACTIONS & HUMAN AWARD */}
            <tr className="bg-slate-50/90 border-t-2 border-slate-200">
              <td className="py-3.5 px-4 font-semibold text-slate-700 bg-slate-50/60 border-r border-slate-200">
                <div className="font-semibold text-slate-900">Procurement Action</div>
                <div className="text-[10px] text-slate-400 font-normal mt-0.5">
                  Human evaluation determination
                </div>
              </td>
              {bids.map((bid) => (
                <td key={bid.quotationId} className="py-3.5 px-4 border-r border-slate-200 last:border-r-0">
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onOpenSupplierDossier(bid)}
                      className="text-xs flex-1 py-1"
                      leftIcon={<Eye className="w-3.5 h-3.5" />}
                    >
                      Dossier
                    </Button>

                    <Link to={ROUTES.QUOTATION_REVIEW(bid.quotationId)}>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs px-2.5 py-1 text-indigo-600 hover:bg-indigo-50"
                        title="Review AI Extracted Document"
                      >
                        <FileSearch className="w-3.5 h-3.5" />
                      </Button>
                    </Link>
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  );
};
