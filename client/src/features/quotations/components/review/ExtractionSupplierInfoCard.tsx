import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../../components/ui/Card';
import { Input } from '../../../../components/ui/Input';
import { Badge } from '../../../../components/ui/Badge';
import { EvidenceBadge } from './EvidenceBadge';
import type { ExtractedSupplierData, FieldEvidence } from '../../types/extraction';
import { Building2, User, Mail, Phone, MapPin, Hash } from 'lucide-react';

interface ExtractionSupplierInfoCardProps {
  supplier: ExtractedSupplierData;
  evidenceMap?: Record<string, FieldEvidence>;
  onChange: (field: keyof ExtractedSupplierData, value: string) => void;
  onEvidenceClick?: (fieldName: string, evidence: FieldEvidence) => void;
  isReadOnly?: boolean;
}

export const ExtractionSupplierInfoCard: React.FC<ExtractionSupplierInfoCardProps> = ({
  supplier,
  evidenceMap = {},
  onChange,
  onEvidenceClick,
  isReadOnly = false,
}) => {
  const getEvidence = (fieldKey: string): FieldEvidence | undefined => {
    return evidenceMap[`supplier.${fieldKey}`] || evidenceMap[fieldKey];
  };

  const handleEvidenceClick = (fieldKey: string) => {
    const ev = getEvidence(fieldKey);
    if (ev && onEvidenceClick) {
      onEvidenceClick(`Supplier ${fieldKey}`, ev);
    }
  };

  return (
    <Card className="border-slate-200 shadow-2xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-slate-900">
                Supplier & Vendor Information
              </CardTitle>
              <p className="text-[11px] text-slate-500">
                Extracted organization identity, contact credentials, and reference
              </p>
            </div>
          </div>
          <Badge variant="neutral" size="sm">
            AI Extracted
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Supplier Name & Quotation Number */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-slate-400" />
                <span>Supplier / Vendor Name</span>
                {!supplier.supplier_name && (
                  <span className="text-[10px] font-semibold text-rose-600 bg-rose-50 px-1 rounded border border-rose-200">
                    Required
                  </span>
                )}
              </label>
              <div onClick={() => handleEvidenceClick('supplier_name')}>
                <EvidenceBadge
                  evidence={getEvidence('supplier_name')}
                  fieldName="Supplier Name"
                />
              </div>
            </div>
            <Input
              value={supplier.supplier_name || ''}
              onChange={(e) => onChange('supplier_name', e.target.value)}
              placeholder="e.g. Precision Components Ltd."
              disabled={isReadOnly}
              className={!supplier.supplier_name ? 'border-rose-300 focus:border-rose-500' : ''}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-slate-400" />
                <span>Supplier Quotation #</span>
              </label>
              <div onClick={() => handleEvidenceClick('quotation_number')}>
                <EvidenceBadge
                  evidence={getEvidence('quotation_number')}
                  fieldName="Quotation Number"
                />
              </div>
            </div>
            <Input
              value={supplier.quotation_number || ''}
              onChange={(e) => onChange('quotation_number', e.target.value)}
              placeholder="e.g. QT-2026-9921"
              disabled={isReadOnly}
            />
          </div>
        </div>

        {/* Contact Person & Email */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span>Contact Person / Sales Rep</span>
              </label>
              <div onClick={() => handleEvidenceClick('contact_person')}>
                <EvidenceBadge
                  evidence={getEvidence('contact_person')}
                  fieldName="Contact Person"
                />
              </div>
            </div>
            <Input
              value={supplier.contact_person || ''}
              onChange={(e) => onChange('contact_person', e.target.value)}
              placeholder="e.g. Sarah Jenkins"
              disabled={isReadOnly}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                <span>Contact Email</span>
              </label>
              <div onClick={() => handleEvidenceClick('email')}>
                <EvidenceBadge evidence={getEvidence('email')} fieldName="Email" />
              </div>
            </div>
            <Input
              type="email"
              value={supplier.email || ''}
              onChange={(e) => onChange('email', e.target.value)}
              placeholder="e.g. sales@precisioncomp.com"
              disabled={isReadOnly}
            />
          </div>
        </div>

        {/* Phone & Physical Address */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                <span>Phone Number</span>
              </label>
              <div onClick={() => handleEvidenceClick('phone')}>
                <EvidenceBadge evidence={getEvidence('phone')} fieldName="Phone" />
              </div>
            </div>
            <Input
              value={supplier.phone || ''}
              onChange={(e) => onChange('phone', e.target.value)}
              placeholder="e.g. +1 (555) 234-5678"
              disabled={isReadOnly}
            />
          </div>

          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>Supplier Business Address</span>
              </label>
              <div onClick={() => handleEvidenceClick('address')}>
                <EvidenceBadge evidence={getEvidence('address')} fieldName="Address" />
              </div>
            </div>
            <Input
              value={supplier.address || ''}
              onChange={(e) => onChange('address', e.target.value)}
              placeholder="e.g. 104 Industrial Parkway, Detroit, MI 48201"
              disabled={isReadOnly}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
