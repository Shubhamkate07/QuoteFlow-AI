import React from 'react';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import type { Rfq } from '../../rfq/types';
import { formatDate } from '../../../utils/formatters';
import {
  FileText,
  FileSpreadsheet,
  Layers,
  Calendar,
  Building,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

interface ReportHeaderProps {
  rfqs: Rfq[];
  selectedRfq: Rfq;
  onSelectRfq: (rfqId: string) => void;
  onTriggerExport: (format: 'pdf' | 'excel') => void;
  onOpenExportModal?: (format: 'pdf' | 'excel') => void;
  isExportingExcel?: boolean;
  isExportingPdf?: boolean;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({
  rfqs,
  selectedRfq,
  onSelectRfq,
  onTriggerExport,
  onOpenExportModal,
  isExportingExcel = false,
  isExportingPdf = false,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 mb-6">
      {/* Top Banner: Corporate Document Identifiers */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-5 border-b border-slate-100 gap-4">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            <span className="flex items-center gap-1 text-indigo-600">
              <Building className="w-3.5 h-3.5" />
              QuoteFlow Global Procurement
            </span>
            <span>•</span>
            <span className="font-mono">Doc ID: DOC-EV-{selectedRfq.rfqNumber.replace('RFQ-', '')}</span>
            <span>•</span>
            <span className="font-mono">Rev 1.0</span>
          </div>

          <h1 className="text-xl font-extrabold text-slate-900 mt-1 tracking-tight">
            Procurement Sourcing Evaluation & Award Recommendation Report
          </h1>

          <p className="text-xs text-slate-500 mt-1">
            Package: <strong className="text-slate-800">{selectedRfq.title}</strong> ({selectedRfq.rfqNumber})
          </p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onTriggerExport('excel')}
            isLoading={isExportingExcel}
            className="text-xs text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300"
            leftIcon={<FileSpreadsheet className="w-4 h-4 text-emerald-600" />}
          >
            Export Excel (.xlsx)
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => onTriggerExport('pdf')}
            isLoading={isExportingPdf}
            className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
            leftIcon={<FileText className="w-4 h-4" />}
          >
            Export PDF Report
          </Button>

          {onOpenExportModal && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenExportModal('pdf')}
              className="text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              title="Deliverable export options & contents preview"
            >
              Export Options...
            </Button>
          )}
        </div>
      </div>

      {/* Package Selector & Meta Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 text-xs">
        {/* RFQ Switcher */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-indigo-600" />
            <span>Select RFQ Package</span>
          </label>
          <Select
            value={selectedRfq.id}
            onChange={(e) => onSelectRfq(e.target.value)}
            options={rfqs.map((r) => ({
              value: r.id,
              label: `${r.rfqNumber}: ${r.title.substring(0, 32)}...`,
            }))}
          />
        </div>

        {/* Date & Milestone */}
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 space-y-0.5">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px]">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold uppercase tracking-wider">Evaluation Date</span>
          </div>
          <div className="font-semibold text-slate-900">
            {formatDate(new Date().toISOString())}
          </div>
          <div className="text-[10px] text-slate-400">
            Required Delivery: {formatDate(selectedRfq.requiredDeliveryDate)}
          </div>
        </div>

        {/* Budget Cap */}
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 space-y-0.5">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold uppercase tracking-wider">Approved Budget Cap</span>
          </div>
          <div className="font-bold text-slate-900 font-mono text-sm">
            ${(selectedRfq.targetBudget ?? 0).toLocaleString()} {selectedRfq.currency || 'USD'}
          </div>
          <div className="text-[10px] text-slate-400">
            {(selectedRfq.items || []).length} BOM Items in scope
          </div>
        </div>

        {/* Governance Status */}
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 space-y-0.5">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px]">
            <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold uppercase tracking-wider">Governance Status</span>
          </div>
          <div>
            <Badge variant="warning" size="sm" dot>
              Pending Steering Committee Sign-off
            </Badge>
          </div>
          <div className="text-[10px] text-slate-400">
            Prepared by Global Sourcing Lead
          </div>
        </div>
      </div>
    </div>
  );
};
