import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid, BackendSpecMatchingData } from '../../comparison/types';
import type { Rfq } from '../../rfq/types';
import { ShieldCheck, CheckCircle2, XCircle, HelpCircle } from 'lucide-react';

interface SpecificationSummarySectionProps {
  rfq: Rfq;
  bids?: ComparisonSupplierBid[];
  specMatching?: BackendSpecMatchingData;
}

export const SpecificationSummarySection: React.FC<SpecificationSummarySectionProps> = ({
  rfq: _rfq,
  bids = [],
  specMatching,
}) => {
  const summaries = specMatching?.supplier_summaries || [];
  const items = specMatching?.items || [];

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-indigo-600" />
            <CardTitle>3. Technical Specification & Quality Compliance</CardTitle>
          </div>
          <Badge variant="neutral" size="sm">
            Deterministic Technical Audit
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <p className="text-xs text-slate-600 leading-relaxed">
          Evaluation of raw material alloys, precision tolerances, electrical requirements, and drawing standards against RFQ procurement specifications:
        </p>

        {/* Supplier Compliance Summary Cards */}
        {summaries.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {summaries.map((s) => {
              const isCompliant = s.overall_verdict === 'COMPLIANT';
              const isPartial = s.overall_verdict === 'PARTIALLY_COMPLIANT';

              return (
                <div
                  key={s.supplier_id + s.quotation_id}
                  className={`p-4 rounded-xl border space-y-2.5 ${
                    isCompliant
                      ? 'bg-emerald-50/15 border-emerald-200'
                      : isPartial
                      ? 'bg-amber-50/15 border-amber-200'
                      : 'bg-rose-50/15 border-rose-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-xs text-slate-900 truncate max-w-[160px]" title={s.supplier_name}>
                        {s.supplier_name}
                      </h4>
                      {s.quotation_number && (
                        <div className="text-[10px] text-slate-400 font-mono">{s.quotation_number}</div>
                      )}
                    </div>
                    <Badge variant={isCompliant ? 'success' : isPartial ? 'warning' : 'danger'} size="sm">
                      {s.average_score.toFixed(0)}% Match
                    </Badge>
                  </div>

                  {/* Summary Metrics */}
                  <div className="grid grid-cols-3 gap-2 text-center text-xs py-1 border-y border-slate-200/60 font-mono">
                    <div>
                      <span className="text-[9px] text-slate-400 block font-sans">Compliant</span>
                      <strong className="text-emerald-700">{s.compliant_items_count}</strong>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 block font-sans">Partial</span>
                      <strong className="text-amber-700">{s.partially_compliant_items_count}</strong>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 block font-sans">Mismatches</span>
                      <strong className={s.total_critical_mismatches > 0 ? 'text-rose-700 font-bold' : 'text-slate-600'}>
                        {s.total_critical_mismatches}
                      </strong>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-600">
                    Verdict:{' '}
                    <strong className={isCompliant ? 'text-emerald-700' : isPartial ? 'text-amber-700' : 'text-rose-700'}>
                      {s.overall_verdict.replace(/_/g, ' ')}
                    </strong>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {bids.map((bid) => {
              const isFullMatch = bid.specMatchPercentage === 100;
              return (
                <div
                  key={bid.quotationId}
                  className={`p-4 rounded-xl border space-y-2.5 ${
                    isFullMatch
                      ? 'bg-emerald-50/15 border-emerald-200'
                      : 'bg-amber-50/15 border-amber-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-xs text-slate-900 truncate max-w-[160px]" title={bid.supplierName}>
                      {bid.supplierName}
                    </h4>
                    <Badge variant={isFullMatch ? 'success' : 'warning'} size="sm">
                      {bid.specMatchPercentage}% Match
                    </Badge>
                  </div>
                  <div className="text-xs text-slate-600">
                    {isFullMatch
                      ? '100% verified specification compliance across all line items.'
                      : `Specification variance detected: ${bid.materialDeviations[0] || 'Technical parameter deviation'}`}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Detailed Parameter Verification Table */}
        {items.length > 0 && (
          <div className="border border-slate-200 rounded-xl overflow-hidden mt-4">
            <div className="bg-slate-50 p-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700 flex justify-between items-center">
              <span>Parameter-by-Parameter Specification Verification Log:</span>
              <span className="text-[10px] text-slate-400 font-normal">
                Audited against drawing requirements
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Item Scope</th>
                    <th className="py-2.5 px-3">Parameter</th>
                    <th className="py-2.5 px-3">Required Spec</th>
                    <th className="py-2.5 px-3">Supplier Name</th>
                    <th className="py-2.5 px-3">Quoted Value</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                    <th className="py-2.5 px-3">Audit Discrepancy & Citation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((it) =>
                    (it.supplier_matches || []).map((sm) =>
                      (sm.parameter_matches || []).map((pm, pIdx) => {
                        const isMatch = pm.status === 'EXACT_MATCH';
                        const isMismatch = pm.status === 'MISMATCH';

                        return (
                          <tr
                            key={`${it.rfq_item_id}-${sm.supplier_id}-${pIdx}`}
                            className={`hover:bg-slate-50/60 transition-colors ${
                              isMismatch ? 'bg-rose-50/20' : ''
                            }`}
                          >
                            <td className="py-2 px-3 font-medium text-slate-900">
                              {it.rfq_item_name}
                            </td>
                            <td className="py-2 px-3 font-semibold text-slate-800">
                              {pm.parameter}
                            </td>
                            <td className="py-2 px-3 text-slate-600 font-mono">
                              {pm.rfq_value}
                            </td>
                            <td className="py-2 px-3 text-slate-800">
                              {sm.supplier_name}
                            </td>
                            <td className="py-2 px-3 font-mono font-bold text-slate-900">
                              {pm.supplier_value}
                            </td>
                            <td className="py-2 px-3 text-center">
                              {isMatch ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-100 px-1.5 py-0.5 rounded">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  MATCH
                                </span>
                              ) : isMismatch ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-800 bg-rose-100 px-1.5 py-0.5 rounded">
                                  <XCircle className="w-3 h-3 text-rose-600" />
                                  MISMATCH
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded">
                                  <HelpCircle className="w-3 h-3 text-amber-600" />
                                  {pm.status}
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-3 text-slate-600 text-[11px]">
                              <div>{pm.explanation}</div>
                              {pm.evidence && (
                                <div className="text-[10px] text-slate-400 font-mono">
                                  Evidence: {pm.evidence}
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
