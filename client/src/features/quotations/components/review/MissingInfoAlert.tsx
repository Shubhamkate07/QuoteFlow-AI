import React from 'react';
import { AlertCircle, AlertTriangle } from 'lucide-react';

interface MissingInfoAlertProps {
  missingFields?: string[];
  reviewNotes?: string;
  onResolveField?: (fieldKey: string) => void;
}

export const MissingInfoAlert: React.FC<MissingInfoAlertProps> = ({
  missingFields = [],
  reviewNotes,
  onResolveField,
}) => {
  const fieldLabels: Record<string, string> = {
    gstVatNumber: 'Supplier GST / VAT Tax ID',
    warrantyTerms: 'Warranty & SLA Terms',
    deliveryLeadWeeks: 'Delivery Lead Time',
    incoterms: 'Incoterms Standard',
    paymentTerms: 'Payment Terms',
    validUntil: 'Quote Validity Expiration Date',
  };

  const hasMissing = missingFields.length > 0;
  const hasNotes = Boolean(reviewNotes);

  if (!hasMissing && !hasNotes) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* Missing Information Banner */}
      {hasMissing && (
        <div className="p-4 bg-rose-50/80 border border-rose-200 rounded-xl text-xs text-rose-900 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold text-rose-800 block text-xs">
                Missing Information Detected in Supplier Document
              </span>
              <p className="mt-0.5 text-rose-700 leading-relaxed text-[11px]">
                The AI extraction engine could not locate the following required procurement parameters. Please verify the original document on the left and enter the values before approving:
              </p>

              <div className="flex flex-wrap gap-2 mt-2.5">
                {missingFields.map((field) => (
                  <button
                    key={field}
                    type="button"
                    onClick={() => onResolveField?.(field)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-rose-300 text-rose-800 text-[11px] font-medium hover:bg-rose-100 hover:border-rose-400 transition-colors shadow-2xs"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                    <span>Missing: {fieldLabels[field] || field}</span>
                    <span className="text-[10px] text-rose-500 underline ml-0.5">Fill in</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Review & Variance Note Banner */}
      {hasNotes && (
        <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-xl text-xs text-amber-900 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-amber-800 text-xs">
                  Specification Variance & Verification Alert
                </span>
                <span className="px-1.5 py-0.5 rounded bg-amber-200/60 text-amber-900 text-[10px] font-mono font-medium">
                  Gemini Audit
                </span>
              </div>
              <p className="mt-1 text-amber-800 leading-relaxed text-[11px]">
                {reviewNotes}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
