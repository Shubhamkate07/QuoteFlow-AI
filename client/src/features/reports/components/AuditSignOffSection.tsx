import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { FileCheck } from 'lucide-react';
import { formatDate } from '../../../utils/formatters';

interface AuditSignOffSectionProps {
  rfqNumber: string;
}

export const AuditSignOffSection: React.FC<AuditSignOffSectionProps> = ({ rfqNumber }) => {
  const currentDate = formatDate(new Date().toISOString());

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileCheck className="w-4 h-4 text-indigo-600" />
            <CardTitle>7. Governance Approval & Audit Sign-off</CardTitle>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Audit Dossier: {rfqNumber}
          </span>
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        <p className="text-xs text-slate-500 mb-6">
          Signatures below authenticate that all supplier quotations have been verified against drawing specifications, commercial budgets, and corporate compliance standards:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Signoff 1 */}
          <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              1. Prepared By:
            </span>
            <div className="border-b border-dashed border-slate-300 pb-2 text-xs font-semibold text-slate-900 font-mono">
              Marcus H. Vance
            </div>
            <div className="text-[11px] text-slate-500">
              Lead Sourcing Specialist
            </div>
            <div className="text-[10px] text-slate-400">
              Date: {currentDate}
            </div>
          </div>

          {/* Signoff 2 */}
          <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              2. Technical Endorsement:
            </span>
            <div className="border-b border-dashed border-slate-300 pb-2 text-xs font-semibold text-slate-900 font-mono">
              Dr. Sarah Jenkins, PE
            </div>
            <div className="text-[11px] text-slate-500">
              Senior Manufacturing Quality Lead
            </div>
            <div className="text-[10px] text-slate-400">
              Status: Endorsed without waivers
            </div>
          </div>

          {/* Signoff 3 */}
          <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              3. Final Committee Award:
            </span>
            <div className="border-b border-dashed border-slate-300 pb-2 text-xs text-slate-400 italic">
              [Pending Committee Signature]
            </div>
            <div className="text-[11px] text-slate-500">
              VP of Global Supply Chain / Plant Director
            </div>
            <div className="text-[10px] text-indigo-600 font-medium">
              Action: Ready for PO release upon signature
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
