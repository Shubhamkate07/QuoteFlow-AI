import React from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  Sparkles,
  DollarSign,
  Layers,
  Clock,
  CreditCard,
  ShieldCheck,
  Info,
  HelpCircle,
} from 'lucide-react';

interface ExplainableScoreModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedBid: ComparisonSupplierBid | null;
  allBids?: ComparisonSupplierBid[];
}

export const ExplainableScoreModal: React.FC<ExplainableScoreModalProps> = ({
  isOpen,
  onClose,
  selectedBid,
  allBids = [],
}) => {
  if (!selectedBid) return null;

  const getFactorIcon = (factorId: string) => {
    switch (factorId) {
      case 'price':
        return <DollarSign className="w-4 h-4 text-emerald-600" />;
      case 'spec_match':
        return <Layers className="w-4 h-4 text-indigo-600" />;
      case 'delivery':
        return <Clock className="w-4 h-4 text-sky-600" />;
      case 'payment_terms':
        return <CreditCard className="w-4 h-4 text-purple-600" />;
      case 'warranty':
      default:
        return <ShieldCheck className="w-4 h-4 text-teal-600" />;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Explainable Scoring: ${selectedBid.supplierName}`}
      description={`Transparent factor-by-factor scoring breakdown • Overall Score: ${selectedBid.overallScore}/100 (Rank #${selectedBid.rank})`}
      maxWidth="3xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>Human-in-the-loop: Evaluation committee makes all final award determinations.</span>
          </div>
          <Button variant="primary" size="sm" onClick={onClose}>
            Close Breakdown
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Important Ethical / Guardrail Disclaimer */}
        <div className="p-3.5 bg-indigo-50/70 border border-indigo-200/90 rounded-xl text-xs text-indigo-950 flex items-start gap-2.5 shadow-2xs">
          <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <div className="flex items-center gap-2">
              <strong className="font-semibold text-indigo-900 block text-xs">
                Objective Decision Support Model — Automated Purchasing Disabled
              </strong>
              <DataOriginBadge type="decision" label="Human Award Required" />
            </div>
            QuoteFlow AI does not automatically select, award, or purchase from suppliers. Recommendations and rankings are derived from a transparent, deterministic mathematical rubric to highlight commercial and technical tradeoffs for your procurement committee.
          </div>
        </div>

        {/* Top Summary Banner */}
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h4 className="font-bold text-sm text-slate-900">{selectedBid.supplierName}</h4>
              <Badge variant="primary" size="sm">
                Rank #{selectedBid.rank}
              </Badge>
              {selectedBid.recommendationTag && (
                <Badge variant="neutral" size="sm">
                  {selectedBid.recommendationTag}
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ref: <span className="font-mono text-slate-700">{selectedBid.quoteReference}</span> • Total Quoted:{' '}
              <span className="font-mono font-semibold text-slate-900">
                ${(selectedBid.totalAmount ?? 0).toLocaleString()}
              </span>
            </p>
          </div>

          <div className="text-right">
            <div className="flex items-center justify-end gap-1 mb-0.5">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                Composite Weighted Score
              </span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <span className="text-3xl font-black font-mono text-slate-900">
              {selectedBid.overallScore}
              <span className="text-sm font-normal text-slate-400">/100</span>
            </span>
          </div>
        </div>

        {/* 5 Factor Breakdown Cards */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
              Configured Factor Rubric & Mathematical Rationale:
            </span>
            <div className="flex items-center gap-1.5">
              <DataOriginBadge type="calculated" size="xs" label="Formulas" />
              <DataOriginBadge type="decision" size="xs" label="Custom Weights" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {selectedBid.scoreBreakdown.map((factor) => (
              <div
                key={factor.id}
                className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-2xs space-y-2 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-200">
                      {getFactorIcon(factor.id)}
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-slate-900 block">
                        {factor.factorName}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Weight: {factor.weightPercentage}%
                      </span>
                    </div>
                  </div>

                  <div className="text-right font-mono">
                    <span className="text-sm font-bold text-slate-900">
                      {factor.weightedScore}
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      ({factor.rawScore}/100 raw)
                    </span>
                  </div>
                </div>

                {/* Progress Meter */}
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(100, Math.max(0, factor.rawScore))}%` }}
                  />
                </div>

                {/* Plain-English Audit Rationale */}
                <p className="text-[11px] text-slate-600 leading-relaxed bg-slate-50/70 p-2 rounded-lg border border-slate-100">
                  {factor.rationale}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Multi-Supplier Comparison Matrix Table */}
        {allBids.length > 1 && (
          <div className="border border-slate-200 rounded-xl overflow-hidden mt-4">
            <div className="bg-slate-50 p-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>Comparative Multi-Criteria Scores Across All Evaluated Bidders:</span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50/60 border-b border-slate-200 text-slate-500 uppercase text-[10px]">
                <tr>
                  <th className="py-2 px-3">Supplier</th>
                  <th className="py-2 px-2 text-right">Price</th>
                  <th className="py-2 px-2 text-right">Specs</th>
                  <th className="py-2 px-2 text-right">Delivery</th>
                  <th className="py-2 px-2 text-right">Terms</th>
                  <th className="py-2 px-2 text-right">Warranty</th>
                  <th className="py-2 px-3 text-right">Overall Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {allBids.map((bid) => (
                  <tr
                    key={bid.quotationId}
                    className={
                      bid.quotationId === selectedBid.quotationId
                        ? 'bg-indigo-50/40 font-semibold text-indigo-950'
                        : 'text-slate-700'
                    }
                  >
                    <td className="py-2 px-3 font-sans font-medium text-slate-900">
                      {bid.supplierName}
                      {bid.rank === 1 && (
                        <span className="ml-1.5 text-[9px] px-1 py-0.2 rounded bg-indigo-100 text-indigo-800">
                          #1
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {bid.scoreBreakdown.find((f) => f.id === 'price')?.weightedScore || 0}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {bid.scoreBreakdown.find((f) => f.id === 'spec_match')?.weightedScore || 0}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {bid.scoreBreakdown.find((f) => f.id === 'delivery')?.weightedScore || 0}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {bid.scoreBreakdown.find((f) => f.id === 'payment_terms')?.weightedScore || 0}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {bid.scoreBreakdown.find((f) => f.id === 'warranty')?.weightedScore || 0}
                    </td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">
                      {bid.overallScore} / 100
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Limitations of Scoring System Notice */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-600 space-y-1">
          <strong className="text-slate-800 font-semibold block flex items-center gap-1">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            Scoring Model Disclosures & Limitations:
          </strong>
          <ul className="list-disc pl-4 space-y-0.5 text-slate-500">
            <li>Scores evaluate only structured data present in the quotation document and RFQ scope.</li>
            <li>Qualitative attributes such as historical vendor reputation, relationship depth, and factory capacity are not scored automatically.</li>
            <li>Procurement officers are required to conduct due diligence before finalizing awards.</li>
          </ul>
        </div>
      </div>
    </Modal>
  );
};
