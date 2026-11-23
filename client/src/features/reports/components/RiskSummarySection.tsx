import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid, BackendQuotationRiskReport } from '../../comparison/types';
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface RiskSummarySectionProps {
  bids?: ComparisonSupplierBid[];
  riskReports?: BackendQuotationRiskReport[];
}

interface FlattenedRiskItem {
  category: string;
  supplierName: string;
  quotationNumber: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  evidence: string;
  mitigation: string;
}

export const RiskSummarySection: React.FC<RiskSummarySectionProps> = ({
  bids = [],
  riskReports = [],
}) => {
  // Extract real risks from backend riskReports or fallback to bids
  const flattenedRisks: FlattenedRiskItem[] = [];

  if (riskReports && riskReports.length > 0) {
    riskReports.forEach((rep) => {
      (rep.flags || []).forEach((flag) => {
        flattenedRisks.push({
          category: flag.affected_field || flag.type.replace(/_/g, ' '),
          supplierName: rep.supplier_name,
          quotationNumber: rep.quotation_number,
          severity: flag.severity.toLowerCase() as any,
          title: flag.title,
          evidence: flag.evidence || flag.description,
          mitigation: flag.recommended_action || 'Review and clarify terms with supplier prior to purchase.',
        });
      });
    });
  } else if (bids && bids.length > 0) {
    bids.forEach((bid) => {
      const flags = bid.riskFlagDetails || [];
      if (flags.length > 0) {
        flags.forEach((flag) => {
          flattenedRisks.push({
            category: flag.affected_field || flag.type.replace(/_/g, ' '),
            supplierName: bid.supplierName,
            quotationNumber: bid.quoteReference,
            severity: flag.severity.toLowerCase() as any,
            title: flag.title,
            evidence: flag.evidence || flag.description,
            mitigation: flag.recommended_action || 'Review and clarify terms with supplier prior to purchase.',
          });
        });
      } else if (bid.riskFlags && bid.riskFlags.length > 0) {
        bid.riskFlags.forEach((flagStr) => {
          flattenedRisks.push({
            category: 'Quotation Variance',
            supplierName: bid.supplierName,
            quotationNumber: bid.quoteReference,
            severity: bid.riskLevel === 'high' ? 'high' : bid.riskLevel === 'medium' ? 'medium' : 'low',
            title: flagStr,
            evidence: flagStr,
            mitigation: 'Clarify with supplier prior to award.',
          });
        });
      }
    });
  }

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <CardTitle>6. Multi-Factor Risk Assessment & Mitigation Matrix</CardTitle>
          </div>
          <Badge variant={flattenedRisks.length === 0 ? 'success' : 'warning'} size="sm">
            {flattenedRisks.length === 0 ? '0 Exceptions' : `${flattenedRisks.length} Rule Exceptions`}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {flattenedRisks.length === 0 ? (
          <div className="p-8 text-center bg-emerald-50/20 text-emerald-900">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
            <h4 className="font-bold text-sm">No Critical or Commercial Risk Exceptions Detected</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              All evaluated vendor proposals satisfy corporate compliance, arithmetic validation, and delivery timeline criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-2.5 px-4">Risk Category / Scope</th>
                  <th className="py-2.5 px-3">Supplier & Quote</th>
                  <th className="py-2.5 px-3 text-center">Severity</th>
                  <th className="py-2.5 px-4">Identified Risk Factor & Evidence</th>
                  <th className="py-2.5 px-4">Recommended Procurement Mitigation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {flattenedRisks.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-slate-900 text-xs capitalize">
                      {item.category}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-800 text-xs">{item.supplierName}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{item.quotationNumber}</div>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`text-[10px] font-bold uppercase font-mono px-2 py-0.5 rounded ${
                          item.severity === 'critical' || item.severity === 'high'
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : item.severity === 'medium'
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}
                      >
                        {item.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-700 text-xs leading-relaxed max-w-xs">
                      <div className="flex items-start gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-slate-900 block">{item.title}</strong>
                          <span className="text-[11px] text-slate-500">{item.evidence}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-[11px] leading-relaxed bg-slate-50/40">
                      {item.mitigation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
