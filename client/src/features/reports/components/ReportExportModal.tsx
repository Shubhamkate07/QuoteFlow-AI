import React, { useState } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { comparisonApi } from '../../comparison/api/comparisonApi';
import {
  FileText,
  FileSpreadsheet,
  Download,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Table,
  Sliders,
  ShieldCheck,
  Award,
} from 'lucide-react';

export interface ReportExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  format: 'pdf' | 'excel';
  rfqId: string;
  rfqNumber: string;
  onSuccess: (message: string) => void;
  onError?: (error: string) => void;
}

export const ReportExportModal: React.FC<ReportExportModalProps> = ({
  isOpen,
  onClose,
  format,
  rfqId,
  rfqNumber,
  onSuccess,
  onError,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const isPdf = format === 'pdf';
  const cleanNumber = (rfqNumber || rfqId).replace(/[^a-zA-Z0-9_-]/g, '_');
  const today = new Date().toISOString().split('T')[0];
  const fileName = isPdf
    ? `QuoteFlow_${cleanNumber}_Evaluation_Report_${today}.pdf`
    : `QuoteFlow_${cleanNumber}_Comparison_${today}.xlsx`;

  const handleStartExport = async () => {
    if (!rfqId) {
      setDownloadError('RFQ identification is missing.');
      return;
    }

    setIsExporting(true);
    setDownloadError(null);

    try {
      let blob: Blob;
      if (isPdf) {
        blob = await comparisonApi.downloadRfqComparisonPdf(rfqId);
      } else {
        blob = await comparisonApi.downloadRfqComparisonExcel(rfqId);
      }

      // Trigger standard browser download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      onSuccess(`Successfully downloaded ${fileName}`);
      onClose();
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.error ||
        err?.message ||
        'Server encountered an issue generating the document. Please verify approved quotations exist.';
      setDownloadError(errMsg);
      if (onError) onError(errMsg);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isExporting ? () => {} : onClose}
      title={isPdf ? 'Export Executive PDF Evaluation Report' : 'Export Deterministic Excel Workbook'}
      description={`Generate audit-compliant procurement deliverable for ${rfqNumber}.`}
      maxWidth="md"
      footer={
        <div className="flex items-center justify-end gap-3 w-full">
          <Button variant="outline" type="button" onClick={onClose} disabled={isExporting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="button"
            onClick={handleStartExport}
            isLoading={isExporting}
            className={isPdf ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-emerald-600 hover:bg-emerald-700'}
            leftIcon={<Download className="w-4 h-4" />}
          >
            {isExporting ? 'Generating Report...' : `Download ${isPdf ? 'PDF' : 'Excel'}`}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Document Format Preview */}
        <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center space-x-3">
          <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-2xs shrink-0">
            {isPdf ? (
              <FileText className="w-8 h-8 text-rose-600" />
            ) : (
              <FileSpreadsheet className="w-8 h-8 text-emerald-600" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="text-xs font-bold text-slate-900 font-mono truncate">{fileName}</h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {isPdf
                ? 'Publication-grade executive PDF with pagination, header/footer branding, and sign-off block.'
                : 'Deterministic 5-sheet workbook with styled headers, auto-fit columns, and price formulas.'}
            </p>
          </div>
        </div>

        {/* Error Alert if download failed */}
        {downloadError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-2 text-rose-800 text-xs animate-in fade-in">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block">Export Generation Failed</span>
              <p className="text-[11px] text-rose-700 mt-0.5">{downloadError}</p>
            </div>
          </div>
        )}

        {/* Deliverable Contents Overview */}
        <div className="space-y-2">
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
            {isPdf ? 'Included Report Sections:' : 'Workbook Structure (5 Sheets):'}
          </span>

          <div className="space-y-1.5 text-xs text-slate-600">
            {isPdf ? (
              <>
                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">1. Executive Summary & KPIs</span>
                    <span className="text-[11px] text-slate-500">RFQ specifications, participant summary, price spread, and budget target.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Table className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">2. Commercial Price Comparison Matrix</span>
                    <span className="text-[11px] text-slate-500">Subtotals, tax, freight, discount adjustments, and line-item unit pricing.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Sliders className="w-4 h-4 text-sky-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">3. Technical Spec Verification & Commercial Terms</span>
                    <span className="text-[11px] text-slate-500">Parameter compliance statuses, delivery schedules, Incoterms, and payment terms.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">4. Deterministic Risk Flags & Mitigations</span>
                    <span className="text-[11px] text-slate-500">Severity badges, quotation variances, shortfall alerts, and recommended actions.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Award className="w-4 h-4 text-purple-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">5. Explainable Supplier Scoring & Sign-Off</span>
                    <span className="text-[11px] text-slate-500">Factor weight formula, scoring limitations, human governance disclaimer, and signatures.</span>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">Sheet 1: Summary</span>
                    <span className="text-[11px] text-slate-500">RFQ metadata, evaluation timestamp, supplier counts, and price extremes.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Table className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">Sheet 2: Price Comparison</span>
                    <span className="text-[11px] text-slate-500">BOM itemization, unit prices, extended totals, tax, discount, and grand totals.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Sliders className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">Sheet 3: Specification Comparison</span>
                    <span className="text-[11px] text-slate-500">Required vs quoted parameters, match statuses, and discrepancy notes.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">Sheet 4: Commercial Terms</span>
                    <span className="text-[11px] text-slate-500">Delivery lead times, payment terms, and warranty period comparisons.</span>
                  </div>
                </div>

                <div className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-center gap-2.5">
                  <Award className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block">Sheet 5: Risk Flags</span>
                    <span className="text-[11px] text-slate-500">Supplier exceptions, severity levels, detailed evidence, and mitigations.</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Live Export Progression State */}
        {isExporting && (
          <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl space-y-1.5 animate-in fade-in">
            <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-900">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
              <span>Fetching server-generated deliverable and initiating download...</span>
            </div>
            <div className="w-full bg-indigo-200/60 rounded-full h-1.5 overflow-hidden">
              <div className="bg-indigo-600 h-full rounded-full animate-pulse w-3/4" />
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
