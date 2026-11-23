import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../../comparison/types';
import { CreditCard, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface PaymentTermsSummarySectionProps {
  bids: ComparisonSupplierBid[];
}

export const PaymentTermsSummarySection: React.FC<PaymentTermsSummarySectionProps> = ({
  bids,
}) => {
  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <CreditCard className="w-4 h-4 text-purple-600" />
          <CardTitle>5. Commercial Payment Terms & Warranty Analysis</CardTitle>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {bids.map((bid) => {
            const hasAdvance =
              bid.paymentTerms?.toLowerCase().includes('advance') ||
              bid.paymentTerms?.toLowerCase().includes('deposit');
            const hasShortWarranty =
              bid.warrantyTerms?.toLowerCase().includes('no warranty') ||
              bid.warrantyTerms?.toLowerCase().includes('none');

            return (
              <div
                key={bid.quotationId}
                className={`p-4 rounded-xl border space-y-2.5 ${
                  hasAdvance
                    ? 'bg-amber-50/20 border-amber-200'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-900 truncate max-w-[170px]" title={bid.supplierName}>
                    {bid.supplierName}
                  </h4>
                  {hasAdvance ? (
                    <Badge variant="warning" size="sm">
                      <AlertTriangle className="w-3 h-3 mr-1 inline" />
                      Deposit Required
                    </Badge>
                  ) : (
                    <Badge variant="success" size="sm">
                      <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                      Standard Credit
                    </Badge>
                  )}
                </div>

                <div className="space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Payment Terms:</span>
                    <span className={`font-semibold ${hasAdvance ? 'text-amber-800' : 'text-slate-900'}`}>
                      {bid.paymentTerms || 'Net 30'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Warranty Coverage:</span>
                    <span className={`font-semibold ${hasShortWarranty ? 'text-rose-700' : 'text-slate-900'}`}>
                      {bid.warrantyTerms || '12 Months Standard'}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 bg-white rounded-lg border border-slate-200 text-[11px] leading-relaxed">
                  {hasAdvance ? (
                    <span className="text-amber-800 font-medium">
                      ⚠ Cash Prepayment Risk: Upfront deposit required prior to production. Requires corporate financial approval.
                    </span>
                  ) : (
                    <span className="text-emerald-800 font-medium">
                      ✓ Favorable Working Capital: Credit terms align with standard corporate Net 30/60 post-delivery payment cycle.
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
