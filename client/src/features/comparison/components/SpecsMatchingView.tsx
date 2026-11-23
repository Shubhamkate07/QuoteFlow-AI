import React from 'react';
import { Card, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { BackendSpecMatchingData } from '../types';
import type { Rfq } from '../../rfq/types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  PlusCircle,
  Layers,
} from 'lucide-react';

interface SpecsMatchingViewProps {
  rfq: Rfq;
  specsData?: BackendSpecMatchingData;
}

export const SpecsMatchingView: React.FC<SpecsMatchingViewProps> = ({
  rfq: _rfq,
  specsData,
}) => {
  if (!specsData || !specsData.items || specsData.items.length === 0) {
    return (
      <Card className="p-12 text-center text-slate-500">
        <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-800">No Specification Matching Data Available</h4>
        <p className="text-xs text-slate-400 mt-1">
          Generate comparison to evaluate parameter-by-parameter technical compliance.
        </p>
      </Card>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'EXACT_MATCH':
        return (
          <Badge variant="success" size="sm" className="gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Exact Match
          </Badge>
        );
      case 'MISMATCH':
        return (
          <Badge variant="danger" size="sm" className="gap-1">
            <AlertTriangle className="w-3 h-3" />
            Mismatch
          </Badge>
        );
      case 'MISSING':
        return (
          <Badge variant="neutral" size="sm" className="gap-1">
            <AlertTriangle className="w-3 h-3 text-slate-400" />
            Missing
          </Badge>
        );
      case 'UNCLEAR':
        return (
          <Badge variant="warning" size="sm" className="gap-1">
            <HelpCircle className="w-3 h-3" />
            Unclear
          </Badge>
        );
      case 'ADDITIONAL':
        return (
          <Badge variant="neutral" size="sm" className="gap-1">
            <PlusCircle className="w-3 h-3 text-indigo-500" />
            Additional
          </Badge>
        );
      default:
        return <Badge variant="neutral" size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Supplier Compliance Summaries */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {specsData.supplier_summaries.map((s) => (
          <Card key={s.supplier_id} className="border-slate-200">
            <CardContent className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-900">{s.supplier_name}</h4>
                <DataOriginBadge type="ai" size="xs" label="Semantic Match" />
              </div>

              <div className="flex items-baseline justify-between pt-1">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                    Compliance Score
                  </span>
                  <span className="text-2xl font-black font-mono text-slate-900">
                    {Math.round(s.average_score)}%
                  </span>
                </div>

                <Badge
                  variant={
                    s.overall_verdict === 'COMPLIANT'
                      ? 'success'
                      : s.overall_verdict === 'PARTIALLY_COMPLIANT'
                      ? 'warning'
                      : 'danger'
                  }
                  size="sm"
                >
                  {s.overall_verdict}
                </Badge>
              </div>

              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 flex items-center justify-between">
                <span>Critical Mismatches:</span>
                <span
                  className={`font-mono font-bold ${
                    s.total_critical_mismatches > 0 ? 'text-rose-600' : 'text-emerald-700'
                  }`}
                >
                  {s.total_critical_mismatches}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Item-by-Item Parameter Matching Table */}
      <div className="space-y-4">
        {specsData.items.map((item) => (
          <Card key={item.rfq_item_id} className="overflow-hidden border border-slate-200">
            <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h4 className="text-xs font-bold text-slate-900">{item.rfq_item_name}</h4>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  RFQ Requirements: {Object.entries(item.rfq_specs || {}).map(([k, v]) => `${k}: ${v}`).join(' • ')}
                </div>
              </div>
              <DataOriginBadge type="ai" size="xs" label="AI Interpreted" />
            </div>

            <div className="divide-y divide-slate-100">
              {item.supplier_matches.map((suppMatch) => (
                <div key={suppMatch.supplier_id} className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">{suppMatch.supplier_name}</span>
                      <span className="text-[10px] text-slate-400 font-mono">Ref: {suppMatch.quotation_number}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-800">
                        Score: {Math.round(suppMatch.compliance_score)}%
                      </span>
                      <Badge
                        variant={
                          suppMatch.overall_status === 'COMPLIANT'
                            ? 'success'
                            : suppMatch.overall_status === 'PARTIALLY_COMPLIANT'
                            ? 'warning'
                            : 'danger'
                        }
                        size="sm"
                      >
                        {suppMatch.overall_status}
                      </Badge>
                    </div>
                  </div>

                  {/* Parameter Match Grid */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-slate-50/60 text-slate-500 uppercase text-[10px]">
                        <tr>
                          <th className="py-2 px-3">Parameter</th>
                          <th className="py-2 px-3">RFQ Required</th>
                          <th className="py-2 px-3">Supplier Quoted</th>
                          <th className="py-2 px-3">Status</th>
                          <th className="py-2 px-3">Evidence / Explanation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {suppMatch.parameter_matches && suppMatch.parameter_matches.length > 0 ? (
                          suppMatch.parameter_matches.map((param, pIdx) => (
                            <tr key={pIdx} className="hover:bg-slate-50/40">
                              <td className="py-2.5 px-3 font-semibold text-slate-900">
                                {param.parameter}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-slate-700">
                                {param.rfq_value}
                              </td>
                              <td className="py-2.5 px-3 font-mono font-medium text-slate-900">
                                {param.supplier_value}
                              </td>
                              <td className="py-2.5 px-3">
                                {getStatusBadge(param.status)}
                              </td>
                              <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                                <div>{param.explanation}</div>
                                {param.evidence && (
                                  <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                                    Evidence: {param.evidence}
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={5} className="py-2 px-3 text-slate-400 italic">
                              100% compliant with standard RFQ line item specifications.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
