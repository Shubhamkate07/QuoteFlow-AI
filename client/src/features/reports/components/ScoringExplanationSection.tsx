import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { BackendScoringData } from '../../comparison/types';
import { Award, Calculator, Info, ShieldAlert } from 'lucide-react';

interface ScoringExplanationSectionProps {
  scoring?: BackendScoringData;
  weights?: Record<string, number>;
}

export const ScoringExplanationSection: React.FC<ScoringExplanationSectionProps> = ({
  scoring,
  weights,
}) => {
  const activeWeights = scoring?.weights_applied || weights || {
    price: 40,
    spec_match: 30,
    delivery: 15,
    payment_terms: 10,
    warranty: 5,
  };

  const rankings = scoring?.rankings || [];
  const limitations = scoring?.scoring_limitations || [
    'Scoring model assumes linear pricing interpolation within the observed quotation range.',
    'Qualitative supplier relationship history and geopolitical risks are not automatically quantified.',
    'Scoring rankings are decision-support guidelines and do not replace authorized human procurement governance.',
  ];

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Calculator className="w-4 h-4 text-indigo-600" />
            <CardTitle>7. Explainable Supplier Scoring Engine & Factor Breakdown</CardTitle>
          </div>
          <Badge variant="neutral" size="sm">
            Deterministic Formula
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4 text-xs">
        {/* Active Weighting Scheme */}
        <div>
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-2">
            Table 7.1: Active Multi-Attribute Weighting Configuration (Sum = 100%)
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Commercial Price</span>
              <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                {activeWeights.price || 40}%
              </span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Spec Compliance</span>
              <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                {activeWeights.spec_match || 30}%
              </span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Lead Time</span>
              <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                {activeWeights.delivery || 15}%
              </span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Payment Terms</span>
              <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                {activeWeights.payment_terms || 10}%
              </span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Warranty Coverage</span>
              <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                {activeWeights.warranty || 5}%
              </span>
            </div>
          </div>
        </div>

        {/* Per-Supplier Factor Score Breakdown Matrix */}
        {rankings.length > 0 && (
          <div className="border border-slate-200 rounded-xl overflow-hidden mt-3">
            <div className="bg-slate-50 p-2.5 border-b border-slate-200 font-semibold text-slate-700 flex justify-between items-center">
              <span>Table 7.2: Normalized Factor Scores (/100) and Final Score Breakdown</span>
              <span className="text-[10px] text-slate-400 font-normal">
                Final Score = Σ (Factor Score × Weight)
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2 px-3">Supplier Name</th>
                    <th className="py-2 px-3 text-center">Price (/100)</th>
                    <th className="py-2 px-3 text-center">Spec (/100)</th>
                    <th className="py-2 px-3 text-center">Delivery (/100)</th>
                    <th className="py-2 px-3 text-center">Payment (/100)</th>
                    <th className="py-2 px-3 text-center">Warranty (/100)</th>
                    <th className="py-2 px-3 text-center font-bold text-indigo-900 bg-indigo-50/40">
                      Final Score (/100)
                    </th>
                    <th className="py-2 px-3 text-center">Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rankings.map((r) => {
                    const isTop = r.rank === 1;
                    const bdown = r.factors || {};
                    const pScore = bdown.price?.raw_score ?? 0;
                    const sScore = bdown.spec_match?.raw_score ?? 0;
                    const dScore = bdown.delivery?.raw_score ?? 0;
                    const payScore = bdown.payment_terms?.raw_score ?? 0;
                    const wScore = bdown.warranty?.raw_score ?? 0;

                    return (
                      <tr
                        key={r.quotation_id}
                        className={`hover:bg-slate-50/70 transition-colors ${
                          isTop ? 'bg-indigo-50/15' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3">
                          <div className="font-bold text-slate-900">{r.supplier_name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            {r.quotation_number}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono">{pScore.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{sScore.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{dScore.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{payScore.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{wScore.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono font-extrabold text-sm text-indigo-700 bg-indigo-50/30">
                          {r.final_score.toFixed(1)}
                        </td>
                        <td className="py-2.5 px-3 text-center font-bold font-mono">
                          {isTop ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 font-bold">
                              <Award className="w-3.5 h-3.5" />
                              #1
                            </span>
                          ) : (
                            `#${r.rank}`
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Explainable Mathematical Methodology Callout */}
        <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 space-y-1.5 leading-relaxed">
          <div className="flex items-center gap-1.5 font-bold text-slate-900 text-xs">
            <Info className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span>Mathematical Scoring Formulas & Scoring Logic:</span>
          </div>
          <p className="text-[11px] text-slate-600">
            <strong>1. Price Score:</strong> Scaled linearly using formula{' '}
            <code className="text-indigo-700 bg-indigo-50 px-1 py-0.5 rounded">
              Score = 100 × (MaxPrice - Price) / (MaxPrice - MinPrice)
            </code>
            . The lowest bid receives 100 points, highest receives 0 points.
          </p>
          <p className="text-[11px] text-slate-600">
            <strong>2. Specification Score:</strong> Evaluates exact parameter matches, penalizing non-compliant alloys or dimensions based on critical severity deductions.
          </p>
          <p className="text-[11px] text-slate-600">
            <strong>3. Delivery Score:</strong> Fulfilling on or before the RFQ required delivery date yields 100 points; overdue lead times face deterministic weekly deductions.
          </p>
          <p className="text-[11px] text-slate-600">
            <strong>4. Commercial Terms & Warranty:</strong> Standard Net 30/60 trade credit receives full points; advance deposits require risk deductions. Warranty length is benchmarked against 24 months.
          </p>
        </div>

        {/* Scoring Limitations */}
        <div className="p-3 bg-amber-50/40 rounded-xl border border-amber-200 text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-amber-900 text-xs">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>Documented Limitations of the Scoring System:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
            {limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
