import React from 'react';
import { Modal } from '../../../../components/ui/Modal';
import { Button } from '../../../../components/ui/Button';
import { Badge } from '../../../../components/ui/Badge';
import { useExtractionAuditHistory } from '../../hooks/useExtractionQueries';
import {
  History,
  Clock,
  User,
  FileCheck,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { formatDateTime } from '../../../../utils/formatters';

interface AuditHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  extractionId: string;
}

export const AuditHistoryModal: React.FC<AuditHistoryModalProps> = ({
  isOpen,
  onClose,
  extractionId,
}) => {
  const { data, isLoading, error } = useExtractionAuditHistory(
    isOpen ? extractionId : undefined
  );

  const auditEntries = data?.corrections || [];

  const formatValue = (val: any) => {
    if (val === null || val === undefined) return <span className="text-slate-400 italic">null</span>;
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Extraction Audit & Correction History"
      description="Immutable audit log of all human modifications made to AI-extracted quotation values."
      maxWidth="lg"
      footer={
        <div className="flex justify-end w-full">
          <Button variant="outline" type="button" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-2 text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            <span className="text-xs">Loading audit trail...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Failed to load audit history: </span>
              {error instanceof Error ? error.message : 'Unknown error'}
            </div>
          </div>
        ) : auditEntries.length === 0 ? (
          <div className="py-12 text-center text-slate-400 space-y-2">
            <History className="w-10 h-10 mx-auto text-slate-300" />
            <p className="text-xs font-medium text-slate-600">No human corrections recorded yet.</p>
            <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
              Any edits made to supplier info, quotation metadata, line items, or commercial terms will be recorded here with user identity and timestamp.
            </p>
          </div>
        ) : (
          <div className="relative border-l-2 border-indigo-200 ml-3 pl-5 space-y-6">
            {auditEntries.map((entry) => (
              <div key={entry.id} className="relative group">
                {/* Timeline node */}
                <div className="absolute -left-[27px] top-1 w-3.5 h-3.5 rounded-full bg-indigo-600 ring-4 ring-white" />

                <div className="bg-slate-50 rounded-xl border border-slate-200 p-3.5 space-y-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {entry.field_path}
                      </span>
                      <Badge variant="neutral" size="sm">
                        {entry.correction_type}
                      </Badge>
                    </div>

                    <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-slate-400" />
                        {entry.corrected_by_email || 'System / Reviewer'}
                      </span>
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {formatDateTime(entry.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* Old vs New Value comparison */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
                    <div className="p-2 rounded bg-rose-50/70 border border-rose-200">
                      <span className="text-[10px] uppercase font-bold text-rose-500 font-sans block mb-0.5">
                        Previous Value (AI Extracted):
                      </span>
                      <span className="text-rose-900 break-all font-semibold">
                        {formatValue(entry.previous_value)}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-emerald-50/70 border border-emerald-200">
                      <span className="text-[10px] uppercase font-bold text-emerald-600 font-sans block mb-0.5">
                        New Corrected Value:
                      </span>
                      <span className="text-emerald-950 break-all font-semibold">
                        {formatValue(entry.new_value)}
                      </span>
                    </div>
                  </div>

                  {entry.reason && (
                    <div className="text-[11px] text-slate-600 bg-white p-2 rounded border border-slate-100 flex items-start gap-1.5">
                      <FileCheck className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
                      <span>
                        <strong className="text-slate-700">Reason:</strong> {entry.reason}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};
