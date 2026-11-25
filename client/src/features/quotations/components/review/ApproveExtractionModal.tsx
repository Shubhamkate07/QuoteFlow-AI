import React, { useState } from 'react';
import { Modal } from '../../../../components/ui/Modal';
import { Button } from '../../../../components/ui/Button';
import type { BackendQuotationExtraction } from '../../types/extraction';
import { formatCurrency } from '../../../../utils/formatters';
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Loader2,
} from 'lucide-react';

interface ApproveExtractionModalProps {
  isOpen: boolean;
  onClose: () => void;
  extraction: BackendQuotationExtraction;
  existingItemCount?: number;
  onConfirmApprove: (payload: { review_notes?: string; apply_to_quotation?: boolean; replace_items?: boolean }) => void;
  isApproving?: boolean;
  error?: string | null;
}

export const ApproveExtractionModal: React.FC<ApproveExtractionModalProps> = ({
  isOpen,
  onClose,
  extraction,
  existingItemCount,
  onConfirmApprove,
  isApproving = false,
  error = null,
}) => {
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [applyToQuotation, setApplyToQuotation] = useState<boolean>(true);
  const [replaceItems] = useState<boolean>(true);

  const errorFlags = (extraction.validation_flags || []).filter((f) => f.severity === 'ERROR');
  const warningFlags = (extraction.validation_flags || []).filter((f) => f.severity === 'WARNING');
  const hasErrors = errorFlags.length > 0;
  const hasWarnings = warningFlags.length > 0;

  const displayTotal = extraction.calculated_grand_total !== null && extraction.calculated_grand_total !== undefined
    ? Number(extraction.calculated_grand_total)
    : Number(extraction.stated_grand_total) || 0;

  const handleApprove = () => {
    onConfirmApprove({
      review_notes: reviewNotes.trim() || undefined,
      apply_to_quotation: applyToQuotation,
      replace_items: replaceItems,
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Approve AI-Extracted Quotation"
      description="Formal procurement sign-off. Approved data will be marked as human-verified and can be applied to official quotation comparisons."
      maxWidth="md"
      footer={
        <div className="flex items-center justify-end gap-3 w-full">
          <Button variant="outline" type="button" onClick={onClose} disabled={isApproving}>
            Continue Reviewing
          </Button>
          <Button
            variant="primary"
            type="button"
            onClick={handleApprove}
            disabled={isApproving}
            className="bg-emerald-600 hover:bg-emerald-700 text-white focus:ring-emerald-500"
            leftIcon={
              isApproving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ShieldCheck className="w-4 h-4" />
              )
            }
          >
            {isApproving ? 'Approving...' : 'Approve & Finalize'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Error Alert Banner */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-xs text-rose-800 animate-in fade-in">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Approval failed:</span>
              <p className="mt-0.5 text-rose-700 leading-relaxed text-[11px]">{error}</p>
            </div>
          </div>
        )}

        {/* Verification Summary Card */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-500">Supplier / Vendor:</span>
            <span className="font-semibold text-slate-900">{extraction.supplier_name || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Quote Reference:</span>
            <span className="font-mono font-medium text-slate-800">
              {extraction.quotation_number || 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Verified Line Items:</span>
            <span className="font-medium text-slate-900">{extraction.items_count} Items</span>
          </div>
          <div className="flex justify-between pt-2 border-t border-slate-200 text-sm">
            <span className="font-semibold text-slate-700">Final Reconciled Total:</span>
            <span className="font-extrabold font-mono text-emerald-700">
              {formatCurrency(displayTotal, extraction.currency)}
            </span>
          </div>
        </div>

        {/* Validation Warnings notice */}
        {hasErrors && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-xs text-rose-800">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Notice: {errorFlags.length} Validation Error(s) Outstanding</span>
              <p className="mt-0.5 text-rose-700 leading-relaxed text-[11px]">
                Deterministic validation detected potential calculation or schema errors. You can still approve with human override, but please double check line items and totals.
              </p>
            </div>
          </div>
        )}

        {hasWarnings && !hasErrors && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Notice: Validation Warnings Present</span>
              <p className="mt-0.5 text-amber-700 leading-relaxed text-[11px]">
                There are minor validation flags (e.g., date formats or missing optional fields).
              </p>
            </div>
          </div>
        )}

        {/* Review Notes */}
        <div>
          <label className="text-xs font-medium text-slate-700 block mb-1">
            Reviewer Notes / Sign-off Comments (Optional)
          </label>
          <textarea
            rows={3}
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="e.g. Verified with supplier sales rep. Price match confirmed against PO-882."
            className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>

        {/* Checkbox: Apply to quotation */}
        {extraction.quotation_id && (
          <div className="space-y-2 pt-1">
            <div className="flex items-start gap-2">
              <input
                id="apply-to-quotation-checkbox"
                type="checkbox"
                checked={applyToQuotation}
                onChange={(e) => setApplyToQuotation(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              <label
                htmlFor="apply-to-quotation-checkbox"
                className="text-xs text-slate-700 select-none cursor-pointer"
              >
                <strong className="text-slate-900 font-semibold block">
                  Apply data to official Quotation record
                </strong>
                Synchronize supplier details, line items, and financial totals directly to the linked RFQ quotation.
              </label>
            </div>

            {applyToQuotation && (
              <div className="ml-6 p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800">
                Notice: This will replace {existingItemCount ?? extraction.items_count} existing line items extracted previously. Any manually added items will be safely preserved.
              </div>
            )}
          </div>
        )}

        <div className="flex items-start gap-2 pt-1 text-xs text-slate-500">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <p>
            Approved extractions are locked as <strong className="text-slate-800">Verified by Human</strong>. An audit record is stored with your user credentials.
          </p>
        </div>
      </div>
    </Modal>
  );
};
