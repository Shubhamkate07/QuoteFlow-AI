import React from 'react';
import { Card, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { BackendQuotationRiskReport } from '../types';
import type { Rfq } from '../../rfq/types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Info,
  ShieldCheck,
} from 'lucide-react';

interface RiskFlagsViewProps {
  rfq: Rfq;
  riskReports?: BackendQuotationRiskReport[];
}

export const RiskFlagsView: React.FC<RiskFlagsViewProps> = ({
  rfq: _rfq,
  riskReports,
}) => {
  if (!riskReports || riskReports.length === 0) {
    return (
      <Card className="p-12 text-center text-slate-500">
        <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-800">Zero Commercial or Contract Risks</h4>
        <p className="text-xs text-slate-400 mt-1">
          All evaluated quotation documents fulfill standard procurement criteria without risk exceptions.
        </p>
      </Card>
    );
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return <Badge variant="danger" size="sm">{severity}</Badge>;
      case 'MEDIUM':
        return <Badge variant="warning" size="sm">{severity}</Badge>;
      case 'LOW':
      default:
        return <Badge variant="neutral" size="sm">{severity || 'LOW'}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Informational Guidance Banner */}
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 flex items-start gap-3">
        <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <div className="flex items-center gap-2">
            <strong className="text-slate-900 font-semibold block text-xs">
              Deterministic 14-Rule Quotation Audit Engine
            </strong>
            <DataOriginBadge type="risk" size="xs" label="Objective Rules" />
          </div>
          Risk flags are generated deterministically by testing extracted quotation parameters against strict procurement policies (including specification mismatch, missing warranty, cash flow advance deposit risk, delivery delay, and quotation expiration). No generative AI is used to invent risk flags.
        </div>
      </div>

      {/* Reports per Supplier */}
      <div className="space-y-4">
        {riskReports.map((report) => (
          <Card key={report.quotation_id} className="overflow-hidden border border-slate-200">
            {/* Header */}
            <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-bold text-slate-900">{report.supplier_name}</h4>
                  <span
                    className={`text-[10px] font-bold uppercase font-mono px-2 py-0.5 rounded ${
                      report.overall_risk_level?.toUpperCase() === 'LOW'
                        ? 'bg-emerald-100 text-emerald-800'
                        : report.overall_risk_level?.toUpperCase() === 'MEDIUM'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {report.overall_risk_level} Risk Profile
                  </span>
                </div>
                <span className="text-xs text-slate-500 font-mono mt-0.5 block">
                  Quote Reference: {report.quotation_number}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                <div className="text-slate-600">
                  Total Flags:{' '}
                  <span className="font-bold text-slate-900">{report.flags?.length || 0}</span>
                </div>
                {report.high_severity_count > 0 && (
                  <div className="text-rose-600 font-bold">
                    High: {report.high_severity_count}
                  </div>
                )}
                {report.medium_severity_count > 0 && (
                  <div className="text-amber-700 font-bold">
                    Medium: {report.medium_severity_count}
                  </div>
                )}
              </div>
            </div>

            {/* List of Flags */}
            <CardContent className="p-4">
              {report.flags && report.flags.length > 0 ? (
                <div className="space-y-3">
                  {report.flags.map((flag, fIdx) => (
                    <div
                      key={fIdx}
                      className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-2 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <AlertTriangle
                            className={`w-4 h-4 shrink-0 ${
                              flag.severity?.toUpperCase() === 'HIGH' || flag.severity?.toUpperCase() === 'CRITICAL'
                                ? 'text-rose-600'
                                : 'text-amber-500'
                            }`}
                          />
                          <span className="text-xs font-bold text-slate-900">{flag.title}</span>
                          <span className="text-[10px] text-slate-400 font-mono">({flag.type})</span>
                        </div>
                        {getSeverityBadge(flag.severity)}
                      </div>

                      <p className="text-xs text-slate-700 leading-relaxed pl-6">
                        {flag.description}
                      </p>

                      <div className="pl-6 space-y-1 text-[11px]">
                        {flag.affected_field && (
                          <div className="text-slate-500">
                            <span className="font-medium text-slate-700">Affected Parameter:</span>{' '}
                            <span className="font-mono text-slate-800">{flag.affected_field}</span>
                          </div>
                        )}

                        {flag.evidence && (
                          <div className="text-slate-500">
                            <span className="font-medium text-slate-700">Audit Evidence:</span>{' '}
                            <span className="font-mono text-slate-800">{flag.evidence}</span>
                          </div>
                        )}

                        {flag.recommended_action && (
                          <div className="mt-2 p-2 rounded-lg bg-indigo-50/70 border border-indigo-100 text-indigo-950 flex items-start gap-1.5 font-medium">
                            <ArrowRight className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                            <span>
                              <strong>Recommended Mitigation:</strong> {flag.recommended_action}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center space-x-2 text-xs text-emerald-700 font-medium py-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>No commercial, technical, or financial risk flags identified for this quotation.</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
