import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../../comparison/types';
import { formatCurrency } from '../../../utils/formatters';
import { Layers } from 'lucide-react';

interface SupplierComparisonSummarySectionProps {
  bids: ComparisonSupplierBid[];
  currency: string;
}

export const SupplierComparisonSummarySection: React.FC<SupplierComparisonSummarySectionProps> = ({
  bids,
  currency,
}) => {
  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-600" />
            <CardTitle>1. Executive Supplier Scorecard Summary</CardTitle>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            {bids.length} Evaluated Proposals
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-2.5 px-4">Rank & Supplier</th>
                <th className="py-2.5 px-3 text-center">Score (/100)</th>
                <th className="py-2.5 px-3 text-right">Quoted Bid</th>
                <th className="py-2.5 px-3 text-right">Budget Variance</th>
                <th className="py-2.5 px-3 text-center">Spec Match</th>
                <th className="py-2.5 px-3 text-center">Lead Time</th>
                <th className="py-2.5 px-3">Payment Terms</th>
                <th className="py-2.5 px-4 text-center">Risk Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bids.map((bid) => (
                <tr
                  key={bid.quotationId}
                  className={`hover:bg-slate-50/70 transition-colors ${
                    bid.rank === 1 ? 'bg-indigo-50/15' : ''
                  }`}
                >
                  {/* Supplier & Rank */}
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] font-mono shrink-0 ${
                          bid.rank === 1
                            ? 'bg-indigo-600 text-white'
                            : bid.rank === 2
                            ? 'bg-slate-200 text-slate-800'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {bid.rank}
                      </span>
                      <div>
                        <div className="font-bold text-slate-900 text-xs">{bid.supplierName}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          Ref: {bid.quoteReference}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Score */}
                  <td className="py-3 px-3 text-center">
                    <span className="font-bold font-mono text-sm text-slate-900">
                      {bid.overallScore}
                    </span>
                  </td>

                  {/* Quoted Bid */}
                  <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 text-xs">
                    {formatCurrency(bid.totalAmount, currency)}
                    {bid.isLowestTotalAmount && (
                      <span className="ml-1 text-[9px] px-1 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold">
                        Lowest
                      </span>
                    )}
                  </td>

                  {/* Budget Variance */}
                  <td className="py-3 px-3 text-right font-mono text-[11px]">
                    {bid.varianceVsBudget < 0 ? (
                      <span className="text-emerald-700 font-medium">
                        -{formatCurrency(Math.abs(bid.varianceVsBudget), currency)} (
                        {Math.abs(bid.variancePercentage)}%)
                      </span>
                    ) : (
                      <span className="text-rose-600 font-medium">
                        +{formatCurrency(bid.varianceVsBudget, currency)} (+{bid.variancePercentage}%)
                      </span>
                    )}
                  </td>

                  {/* Spec Match */}
                  <td className="py-3 px-3 text-center">
                    <Badge
                      variant={
                        bid.specMatchPercentage === 100
                          ? 'success'
                          : bid.specMatchPercentage >= 90
                          ? 'info'
                          : 'warning'
                      }
                      size="sm"
                    >
                      {bid.specMatchPercentage}%
                    </Badge>
                  </td>

                  {/* Lead Time */}
                  <td className="py-3 px-3 text-center font-mono text-xs text-slate-800">
                    <span className={bid.deliveryLeadWeeks > 4 ? 'text-amber-700 font-bold' : ''}>
                      {bid.deliveryLeadWeeks} Wks
                    </span>
                  </td>

                  {/* Payment Terms */}
                  <td className="py-3 px-3 text-[11px] text-slate-700 font-medium truncate max-w-[140px]" title={bid.paymentTerms}>
                    {bid.paymentTerms}
                  </td>

                  {/* Risk Rating */}
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`text-[10px] font-bold uppercase font-mono px-2 py-0.5 rounded ${
                        bid.riskLevel === 'low'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : bid.riskLevel === 'medium'
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}
                    >
                      {bid.riskLevel}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};
