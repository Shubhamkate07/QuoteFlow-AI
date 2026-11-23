import React from 'react';
import { Link } from 'react-router-dom';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../types';
import { formatCurrency } from '../../../utils/formatters';
import { ROUTES } from '../../../routes/paths';
import { DataOriginBadge } from './DataOriginBadge';
import {
  Truck,
  CreditCard,
  AlertTriangle,
  FileSearch,
  ShieldCheck,
  CheckCircle2,
  FileText,
  UserCheck,
} from 'lucide-react';

interface SupplierDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  bid: ComparisonSupplierBid | null;
}

export const SupplierDetailDrawer: React.FC<SupplierDetailDrawerProps> = ({
  isOpen,
  onClose,
  bid,
}) => {
  if (!bid) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Supplier Dossier: ${bid.supplierName}`}
      description={`Reference: ${bid.quoteReference} • Evaluated Overall Score: ${bid.overallScore}/100 (Rank #${bid.rank})`}
      maxWidth="3xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <Link to={ROUTES.QUOTATION_REVIEW(bid.quotationId)}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<FileSearch className="w-3.5 h-3.5 text-indigo-600" />}
            >
              Open AI Extraction Review
            </Button>
          </Link>

          <Button variant="primary" size="sm" onClick={onClose}>
            Close Dossier
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Header Overview Card */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-slate-900 text-white font-bold flex items-center justify-center text-base">
              {bid.supplierName.charAt(0)}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h4 className="font-bold text-sm text-slate-900">{bid.supplierName}</h4>
                {bid.isApproved ? (
                  <Badge variant="success" size="sm" className="gap-1">
                    <UserCheck className="w-3 h-3" />
                    Human Approved
                  </Badge>
                ) : (
                  <Badge variant="warning" size="sm">
                    Pending Review
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>
                  Source: <span className="font-mono text-slate-700">{bid.fileName}</span> ({bid.fileSize})
                </span>
                <DataOriginBadge type="extracted" size="xs" />
              </p>
            </div>
          </div>

          <div className="text-right">
            <div className="flex items-center justify-end gap-1 mb-0.5">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                Total Quoted Amount
              </span>
              <DataOriginBadge type="extracted" size="xs" />
            </div>
            <span className="text-2xl font-bold font-mono text-slate-900">
              {formatCurrency(bid.totalAmount, bid.currency)}
            </span>
            {bid.isLowestTotalAmount && (
              <span className="block text-[10px] text-emerald-700 font-bold">
                ★ Lowest Price in RFQ
              </span>
            )}
          </div>
        </div>

        {/* Commercial & Contract Terms */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
              Commercial & Delivery Terms:
            </span>
            <DataOriginBadge type="extracted" size="xs" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-white border border-slate-200 rounded-lg">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <Truck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-medium">Lead Time</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {bid.deliveryLeadWeeks} Calendar Weeks
              </p>
              <span className="text-[10px] text-slate-400 block mt-0.5">
                Status: {bid.onTimeStatus}
              </span>
            </div>

            <div className="p-3 bg-white border border-slate-200 rounded-lg">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-medium">Payment Terms</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">{bid.paymentTerms}</p>
              <span className="text-[10px] text-slate-400 block mt-0.5">Commercial Credit</span>
            </div>

            <div className="p-3 bg-white border border-slate-200 rounded-lg">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <Truck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-medium">Incoterms Standard</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">{bid.incoterms}</p>
              <span className="text-[10px] text-slate-400 block mt-0.5">Delivery Scope</span>
            </div>

            <div className="p-3 bg-white border border-slate-200 rounded-lg">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-medium">Warranty</span>
              </div>
              <p className="text-xs font-semibold text-slate-900 truncate" title={bid.warrantyTerms}>
                {bid.warrantyTerms || '12 Months'}
              </p>
              <span className="text-[10px] text-slate-400 block mt-0.5">Quality Assurance</span>
            </div>
          </div>
        </div>

        {/* Risk & Compliance Audit Assessment */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
              Compliance & Risk Assessment:
            </span>
            <div className="flex items-center gap-1.5">
              <DataOriginBadge type="ai" size="xs" label="AI Match" />
              <DataOriginBadge type="risk" size="xs" label="Deterministic Flags" />
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-600 font-medium">Specification Compliance:</span>
              <div className="flex items-center space-x-1.5">
                <span className="font-mono font-bold text-slate-900">
                  {bid.specMatchPercentage}% Match
                </span>
                {bid.specMatchPercentage === 100 ? (
                  <Badge variant="success" size="sm">
                    Verified Compliant
                  </Badge>
                ) : (
                  <Badge variant="warning" size="sm">
                    Variance Detected
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-200">
              <span className="text-slate-600 font-medium">Overall Risk Classification:</span>
              <span
                className={`text-xs font-semibold uppercase font-mono px-2 py-0.5 rounded ${
                  bid.riskLevel === 'low'
                    ? 'bg-emerald-100 text-emerald-800'
                    : bid.riskLevel === 'medium'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-rose-100 text-rose-800'
                }`}
              >
                {bid.riskLevel} Risk ({bid.riskFlags.length} Flag{bid.riskFlags.length === 1 ? '' : 's'})
              </span>
            </div>

            {/* Detailed Risk Flags with Recommendations */}
            {bid.riskFlagDetails && bid.riskFlagDetails.length > 0 ? (
              <div className="space-y-2 pt-1">
                {bid.riskFlagDetails.map((flag, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-white border border-slate-200 rounded-lg space-y-1 text-[11px]"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-bold text-slate-900">
                        <AlertTriangle
                          className={`w-3.5 h-3.5 ${
                            flag.severity === 'HIGH' || flag.severity === 'CRITICAL'
                              ? 'text-rose-600'
                              : 'text-amber-500'
                          }`}
                        />
                        <span>{flag.title}</span>
                      </div>
                      <Badge
                        variant={
                          flag.severity === 'HIGH' || flag.severity === 'CRITICAL'
                            ? 'danger'
                            : 'warning'
                        }
                        size="sm"
                      >
                        {flag.severity}
                      </Badge>
                    </div>
                    <p className="text-slate-600">{flag.description}</p>
                    {flag.evidence && (
                      <div className="text-slate-500 font-mono text-[10px]">
                        Evidence: {flag.evidence}
                      </div>
                    )}
                    {flag.recommended_action && (
                      <div className="text-indigo-700 bg-indigo-50/60 p-1.5 rounded font-medium text-[10px]">
                        Action: {flag.recommended_action}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center space-x-1.5 text-xs text-emerald-700 font-medium pt-1">
                <CheckCircle2 className="w-4 h-4" />
                <span>Zero commercial or technical risk flags identified.</span>
              </div>
            )}
          </div>
        </div>

        {/* Itemized Pricing Schedule */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
              Itemized Pricing Schedule:
            </span>
            <div className="flex items-center gap-1.5">
              <DataOriginBadge type="extracted" size="xs" label="Unit Price" />
              <DataOriginBadge type="calculated" size="xs" label="Extended" />
            </div>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-2 px-3">Item Key</th>
                  <th className="py-2 px-3 text-right">Unit Price</th>
                  <th className="py-2 px-3 text-right">Extended Total</th>
                  <th className="py-2 px-3">Quoted Material Specification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {Object.entries(bid.lineItemsMap).length > 0 ? (
                  Object.entries(bid.lineItemsMap).map(([itemId, item]) => (
                    <tr key={itemId}>
                      <td className="py-2.5 px-3 font-sans font-medium text-slate-900">
                        {itemId.toUpperCase()}
                        {item.isLowestUnitPrice && (
                          <span className="ml-1.5 text-[9px] px-1 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold">
                            Lowest Price
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                        {formatCurrency(item.unitPrice, bid.currency)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-700">
                        {formatCurrency(item.totalPrice, bid.currency)}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-[11px] text-slate-600">
                        {item.materialSpec}
                        {item.hasVariance && (
                          <span className="block text-[10px] text-amber-700 font-semibold mt-0.5">
                            ⚠ {item.discrepancyNote}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-slate-400 italic">
                      No itemized BOM items available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Modal>
  );
};
