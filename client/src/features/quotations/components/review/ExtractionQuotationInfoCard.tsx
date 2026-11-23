import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../../components/ui/Card';
import { Input } from '../../../../components/ui/Input';
import { Select } from '../../../../components/ui/Select';
import { Badge } from '../../../../components/ui/Badge';
import { EvidenceBadge } from './EvidenceBadge';
import type {
  ExtractedQuotationData,
  ExtractedCommercialTermsData,
  FieldEvidence,
} from '../../types/extraction';
import {
  FileText,
  Calendar,
  Truck,
  CreditCard,
  ShieldCheck,
  Clock,
  Coins,
  FileSpreadsheet,
} from 'lucide-react';

interface ExtractionQuotationInfoCardProps {
  quotation: ExtractedQuotationData;
  commercialTerms: ExtractedCommercialTermsData;
  evidenceMap?: Record<string, FieldEvidence>;
  onQuotationChange: (field: keyof ExtractedQuotationData, value: any) => void;
  onCommercialTermsChange: (field: keyof ExtractedCommercialTermsData, value: string) => void;
  onEvidenceClick?: (fieldName: string, evidence: FieldEvidence) => void;
  isReadOnly?: boolean;
}

export const ExtractionQuotationInfoCard: React.FC<ExtractionQuotationInfoCardProps> = ({
  quotation,
  commercialTerms,
  evidenceMap = {},
  onQuotationChange,
  onCommercialTermsChange,
  onEvidenceClick,
  isReadOnly = false,
}) => {
  const getEvidence = (fieldKey: string): FieldEvidence | undefined => {
    return (
      evidenceMap[fieldKey] ||
      evidenceMap[`quotation.${fieldKey}`] ||
      evidenceMap[`commercial_terms.${fieldKey}`]
    );
  };

  const handleEvidenceClick = (fieldKey: string, label: string) => {
    const ev = getEvidence(fieldKey);
    if (ev && onEvidenceClick) {
      onEvidenceClick(label, ev);
    }
  };

  return (
    <Card className="border-slate-200 shadow-2xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-slate-900">
                Quotation Dates, Currency & Commercial Terms
              </CardTitle>
              <p className="text-[11px] text-slate-500">
                Payment terms, delivery schedule, warranty, and validity window
              </p>
            </div>
          </div>
          <Badge variant="neutral" size="sm">
            Commercial Extraction
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Quote Date, Validity Date, Currency */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>Quotation Issue Date</span>
              </label>
              <div onClick={() => handleEvidenceClick('quotation.quotation_date', 'Quotation Date')}>
                <EvidenceBadge
                  evidence={getEvidence('quotation.quotation_date') || getEvidence('quotation_date')}
                  fieldName="Quotation Date"
                />
              </div>
            </div>
            <Input
              type="date"
              value={quotation.quotation_date || ''}
              onChange={(e) => onQuotationChange('quotation_date', e.target.value)}
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Validity Expiry Date</span>
              </label>
              <div onClick={() => handleEvidenceClick('quotation.validity_date', 'Validity Date')}>
                <EvidenceBadge
                  evidence={getEvidence('quotation.validity_date') || getEvidence('validity_date')}
                  fieldName="Validity Date"
                />
              </div>
            </div>
            <Input
              type="date"
              value={quotation.validity_date || ''}
              onChange={(e) => onQuotationChange('validity_date', e.target.value)}
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Coins className="w-3.5 h-3.5 text-slate-400" />
                <span>Quoted Currency</span>
              </label>
              <div onClick={() => handleEvidenceClick('quotation.currency', 'Currency')}>
                <EvidenceBadge
                  evidence={getEvidence('quotation.currency') || getEvidence('currency')}
                  fieldName="Currency"
                />
              </div>
            </div>
            <Select
              value={quotation.currency || 'USD'}
              onChange={(e) => onQuotationChange('currency', e.target.value)}
              disabled={isReadOnly}
              options={[
                { value: 'USD', label: 'USD ($) - US Dollar' },
                { value: 'EUR', label: 'EUR (€) - Euro' },
                { value: 'GBP', label: 'GBP (£) - British Pound' },
                { value: 'INR', label: 'INR (₹) - Indian Rupee' },
                { value: 'CAD', label: 'CAD ($) - Canadian Dollar' },
                { value: 'AUD', label: 'AUD ($) - Australian Dollar' },
                { value: 'JPY', label: 'JPY (¥) - Japanese Yen' },
                { value: 'CNY', label: 'CNY (¥) - Chinese Yuan' },
                { value: 'SGD', label: 'SGD ($) - Singapore Dollar' },
              ]}
            />
          </div>
        </div>

        {/* Payment Terms, Delivery Time, Delivery Terms */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                <span>Payment Terms</span>
              </label>
              <div onClick={() => handleEvidenceClick('commercial_terms.payment_terms', 'Payment Terms')}>
                <EvidenceBadge
                  evidence={getEvidence('commercial_terms.payment_terms') || getEvidence('payment_terms')}
                  fieldName="Payment Terms"
                />
              </div>
            </div>
            <Input
              value={commercialTerms.payment_terms || ''}
              onChange={(e) => onCommercialTermsChange('payment_terms', e.target.value)}
              placeholder="e.g. Net 30 Days"
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5 text-slate-400" />
                <span>Delivery Lead Time</span>
              </label>
              <div onClick={() => handleEvidenceClick('commercial_terms.delivery_time', 'Delivery Time')}>
                <EvidenceBadge
                  evidence={getEvidence('commercial_terms.delivery_time') || getEvidence('delivery_time')}
                  fieldName="Delivery Time"
                />
              </div>
            </div>
            <Input
              value={commercialTerms.delivery_time || ''}
              onChange={(e) => onCommercialTermsChange('delivery_time', e.target.value)}
              placeholder="e.g. 4-6 Weeks ARO"
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <FileSpreadsheet className="w-3.5 h-3.5 text-slate-400" />
                <span>Delivery Terms / Incoterms</span>
              </label>
              <div onClick={() => handleEvidenceClick('commercial_terms.delivery_terms', 'Delivery Terms')}>
                <EvidenceBadge
                  evidence={getEvidence('commercial_terms.delivery_terms') || getEvidence('delivery_terms')}
                  fieldName="Delivery Terms"
                />
              </div>
            </div>
            <Input
              value={commercialTerms.delivery_terms || ''}
              onChange={(e) => onCommercialTermsChange('delivery_terms', e.target.value)}
              placeholder="e.g. FOB Detroit / EXW"
              disabled={isReadOnly}
            />
          </div>
        </div>

        {/* Warranty and Special Commercial Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                <span>Warranty Terms</span>
              </label>
              <div onClick={() => handleEvidenceClick('commercial_terms.warranty', 'Warranty')}>
                <EvidenceBadge
                  evidence={getEvidence('commercial_terms.warranty') || getEvidence('warranty')}
                  fieldName="Warranty"
                />
              </div>
            </div>
            <Input
              value={commercialTerms.warranty || ''}
              onChange={(e) => onCommercialTermsChange('warranty', e.target.value)}
              placeholder="e.g. 12 Months Standard Manufacturer Warranty"
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <span>Commercial Notes / Special Clauses</span>
              </label>
              <div onClick={() => handleEvidenceClick('commercial_terms.notes', 'Notes')}>
                <EvidenceBadge
                  evidence={getEvidence('commercial_terms.notes') || getEvidence('notes')}
                  fieldName="Notes"
                />
              </div>
            </div>
            <Input
              value={commercialTerms.notes || ''}
              onChange={(e) => onCommercialTermsChange('notes', e.target.value)}
              placeholder="e.g. Prices valid subject to raw material index"
              disabled={isReadOnly}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
