import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../../components/ui/Card';
import { Input } from '../../../../components/ui/Input';
import { Badge } from '../../../../components/ui/Badge';
import { formatCurrency } from '../../../../utils/formatters';
import type { ExtractedQuotationData } from '../../types/extraction';
import {
  Calculator,
  CheckCircle2,
  AlertTriangle,
  Scale,
} from 'lucide-react';

interface ExtractionFinancialsCardProps {
  statedSubtotal?: number | string | null;
  statedTax?: number | string | null;
  statedDiscount?: number | string | null;
  statedShipping?: number | string | null;
  statedGrandTotal?: number | string | null;
  calculatedItemsSubtotal?: number | string | null;
  calculatedGrandTotal?: number | string | null;
  isMathConsistent?: boolean;
  totalVariance?: number | string | null;
  currency: string;
  onQuotationChange: (field: keyof ExtractedQuotationData, value: any) => void;
  isReadOnly?: boolean;
}

export const ExtractionFinancialsCard: React.FC<ExtractionFinancialsCardProps> = ({
  statedSubtotal,
  statedTax,
  statedDiscount,
  statedShipping,
  statedGrandTotal,
  calculatedItemsSubtotal,
  calculatedGrandTotal,
  isMathConsistent = true,
  totalVariance,
  currency = 'USD',
  onQuotationChange,
  isReadOnly = false,
}) => {
  const numStatedSubtotal = statedSubtotal !== null && statedSubtotal !== undefined ? Number(statedSubtotal) : null;
  const numStatedTax = statedTax !== null && statedTax !== undefined ? Number(statedTax) : 0;
  const numStatedDiscount = statedDiscount !== null && statedDiscount !== undefined ? Number(statedDiscount) : 0;
  const numStatedShipping = statedShipping !== null && statedShipping !== undefined ? Number(statedShipping) : 0;
  const numStatedGrandTotal = statedGrandTotal !== null && statedGrandTotal !== undefined ? Number(statedGrandTotal) : null;

  const numCalcItemsSubtotal = calculatedItemsSubtotal !== null && calculatedItemsSubtotal !== undefined ? Number(calculatedItemsSubtotal) : 0;
  const numCalcGrandTotal = calculatedGrandTotal !== null && calculatedGrandTotal !== undefined ? Number(calculatedGrandTotal) : 0;

  const varianceAmount = totalVariance !== null && totalVariance !== undefined
    ? Number(totalVariance)
    : numStatedGrandTotal !== null
    ? Math.round(Math.abs(numStatedGrandTotal - numCalcGrandTotal) * 100) / 100
    : 0;

  const hasVariance = varianceAmount > 0.01;

  return (
    <Card className="border-slate-200 shadow-2xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <Calculator className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-slate-900">
                Financial Totals & Deterministic Reconciliation
              </CardTitle>
              <p className="text-[11px] text-slate-500">
                Independent Python calculation vs original document stated figures
              </p>
            </div>
          </div>
          <Badge
            variant={isMathConsistent && !hasVariance ? 'success' : 'warning'}
            size="sm"
          >
            {isMathConsistent && !hasVariance ? 'Math Consistent' : 'Variance Detected'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Comparison grid: Stated vs Calculated */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Subtotal */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Sum of Line Items
            </span>
            <div className="font-mono text-base font-bold text-slate-900">
              {formatCurrency(numCalcItemsSubtotal, currency)}
            </div>
            {numStatedSubtotal !== null && (
              <span className="text-[11px] text-slate-500 block font-mono">
                Stated on Doc: {formatCurrency(numStatedSubtotal, currency)}
              </span>
            )}
          </div>

          {/* Tax, Discount, Shipping inputs */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Adjustments & Tax
            </span>
            <div className="grid grid-cols-3 gap-1.5 text-xs">
              <div>
                <label className="text-[10px] text-slate-500 block">Tax</label>
                <Input
                  type="number"
                  step="0.01"
                  value={numStatedTax || ''}
                  onChange={(e) => onQuotationChange('tax', e.target.value === '' ? null : Number(e.target.value))}
                  placeholder="0.00"
                  disabled={isReadOnly}
                  className="py-0.5 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 block">Discount</label>
                <Input
                  type="number"
                  step="0.01"
                  value={numStatedDiscount || ''}
                  onChange={(e) => onQuotationChange('discount', e.target.value === '' ? null : Number(e.target.value))}
                  placeholder="0.00"
                  disabled={isReadOnly}
                  className="py-0.5 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 block">Shipping</label>
                <Input
                  type="number"
                  step="0.01"
                  value={numStatedShipping || ''}
                  onChange={(e) => onQuotationChange('shipping', e.target.value === '' ? null : Number(e.target.value))}
                  placeholder="0.00"
                  disabled={isReadOnly}
                  className="py-0.5 text-xs font-mono"
                />
              </div>
            </div>
          </div>

          {/* Calculated Grand Total */}
          <div className={`p-3 rounded-xl border space-y-1 ${
            hasVariance ? 'bg-amber-50/70 border-amber-300' : 'bg-indigo-50/70 border-indigo-200'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-indigo-900 uppercase tracking-wider">
                Reconciled Grand Total
              </span>
              <Scale className="w-3.5 h-3.5 text-indigo-600" />
            </div>
            <div className="font-mono text-xl font-extrabold text-indigo-950">
              {formatCurrency(numCalcGrandTotal, currency)}
            </div>
            {numStatedGrandTotal !== null && (
              <span className="text-[11px] font-mono text-slate-600 block">
                Stated on Doc: {formatCurrency(numStatedGrandTotal, currency)}
              </span>
            )}
          </div>
        </div>

        {/* Deterministic Reconciliation Banner */}
        {hasVariance ? (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Document Sum Delta Detected: </span>
              The document stated total is{' '}
              <span className="font-mono font-bold">
                {numStatedGrandTotal !== null ? formatCurrency(numStatedGrandTotal, currency) : 'N/A'}
              </span>
              , but the sum of verified line items plus tax/shipping equals{' '}
              <span className="font-mono font-bold">{formatCurrency(numCalcGrandTotal, currency)}</span> (variance of{' '}
              <span className="font-mono font-bold">{formatCurrency(varianceAmount, currency)}</span>).
              Please verify individual line item quantities, unit prices, or document discounts.
            </div>
          </div>
        ) : (
          <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg flex items-center gap-2 text-xs text-emerald-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Deterministic Check Passed:</strong> All line item arithmetic reconciles with the stated grand total of{' '}
              <strong className="font-mono">{formatCurrency(numCalcGrandTotal, currency)}</strong>.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
