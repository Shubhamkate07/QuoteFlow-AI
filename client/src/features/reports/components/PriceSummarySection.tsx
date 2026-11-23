import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import type { ComparisonSupplierBid, BackendPriceComparisonData } from '../../comparison/types';
import type { Rfq } from '../../rfq/types';
import { formatCurrency } from '../../../utils/formatters';
import { DollarSign, Layers } from 'lucide-react';

interface PriceSummarySectionProps {
  rfq: Rfq;
  bids: ComparisonSupplierBid[];
  currency: string;
  priceComparison?: BackendPriceComparisonData;
}

export const PriceSummarySection: React.FC<PriceSummarySectionProps> = ({
  rfq,
  bids,
  currency,
  priceComparison,
}) => {
  if (bids.length === 0 && (!priceComparison || priceComparison.quotations.length === 0)) {
    return null;
  }

  const sortedBids = [...bids].sort((a, b) => a.totalAmount - b.totalAmount);
  const lowestBidAmount =
    priceComparison?.lowest_grand_total ?? (sortedBids.length > 0 ? sortedBids[0].totalAmount : 0);
  const highestBidAmount =
    priceComparison?.highest_grand_total ??
    (sortedBids.length > 0 ? sortedBids[sortedBids.length - 1].totalAmount : 0);
  const lowestBidderName =
    sortedBids.length > 0
      ? sortedBids[0].supplierName
      : priceComparison?.quotations?.find((q) => q.is_lowest_price)?.supplier_name || 'Lowest Bidder';
  const highestBidderName =
    sortedBids.length > 0
      ? sortedBids[sortedBids.length - 1].supplierName
      : priceComparison?.quotations?.[priceComparison.quotations.length - 1]?.supplier_name || 'Highest Bidder';

  const targetBudget = rfq.targetBudget || 0;
  const maxSavings = priceComparison?.max_savings_amount ?? Math.max(0, targetBudget - lowestBidAmount);
  const savingsPct =
    targetBudget > 0
      ? Math.round((maxSavings / targetBudget) * 1000) / 10
      : priceComparison?.max_savings_percentage ?? 0;

  const cherryPickTotal = priceComparison?.cherry_pick_total;
  const cherryPickSavings = priceComparison?.cherry_pick_savings;
  const itemsMatrix = priceComparison?.items_matrix || [];

  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <DollarSign className="w-4 h-4 text-emerald-600" />
            <CardTitle>2. Commercial Price Summary & Cost Savings Analysis</CardTitle>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            {formatCurrency(maxSavings, currency)} ({savingsPct}%) Potential Savings
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Financial KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
              Baseline Budget Cap
            </span>
            <div className="text-base font-bold font-mono text-slate-900 mt-0.5">
              {formatCurrency(targetBudget, currency)}
            </div>
            <span className="text-[10px] text-slate-400">Approved budget ceiling</span>
          </div>

          <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-200">
            <span className="text-[10px] font-semibold text-emerald-800 uppercase tracking-wider block">
              Lowest Quoted Bid
            </span>
            <div className="text-base font-extrabold font-mono text-emerald-700 mt-0.5">
              {formatCurrency(lowestBidAmount, currency)}
            </div>
            <span className="text-[10px] text-emerald-600 font-medium truncate block">
              {lowestBidderName}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
              Highest Quoted Bid
            </span>
            <div className="text-base font-bold font-mono text-slate-900 mt-0.5">
              {formatCurrency(highestBidAmount, currency)}
            </div>
            <span className="text-[10px] text-slate-400 truncate block">{highestBidderName}</span>
          </div>

          <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200">
            <span className="text-[10px] font-semibold text-indigo-800 uppercase tracking-wider block">
              Split-Award Cherry Pick
            </span>
            <div className="text-base font-bold font-mono text-indigo-700 mt-0.5">
              {formatCurrency(cherryPickTotal ?? lowestBidAmount, currency)}
            </div>
            <span className="text-[10px] text-indigo-600 font-medium">
              Save {formatCurrency(cherryPickSavings ?? 0, currency)}
            </span>
          </div>
        </div>

        {/* Itemized BOM Unit Price Schedule */}
        <div className="border border-slate-200 rounded-xl overflow-hidden mt-3">
          <div className="bg-slate-50 p-2.5 border-b border-slate-200 text-xs font-semibold text-slate-700 flex justify-between items-center">
            <div className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>Itemized Bill of Materials (BOM) Line Items Sourcing Schedule:</span>
            </div>
            <span className="text-[10px] text-slate-400 font-normal">
              Green highlight indicates lowest unit cost per part
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50/60 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-4">BOM Part & Target</th>
                  <th className="py-2.5 px-3 text-right">Quantity</th>
                  {bids.map((bid) => (
                    <th key={bid.quotationId} className="py-2.5 px-3 text-right">
                      {bid.supplierName}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {itemsMatrix.length > 0
                  ? itemsMatrix.map((itemRow) => (
                      <tr key={itemRow.rfq_item_id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-2.5 px-4 font-medium text-slate-900">
                          <div>{itemRow.item_name}</div>
                          {itemRow.target_unit_price != null && (
                            <div className="text-[10px] text-slate-400 font-mono">
                              Target: {formatCurrency(itemRow.target_unit_price, currency)} / {itemRow.uom}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          {(itemRow.quantity ?? 0).toLocaleString()} {itemRow.uom || ''}
                        </td>
                        {bids.map((bid) => {
                          const quoteEntry = (itemRow.quotes || []).find(
                            (q) => q.quotation_id === bid.quotationId || q.supplier_id === bid.supplierId
                          );
                          if (!quoteEntry) {
                            return (
                              <td key={bid.quotationId} className="py-2.5 px-3 text-right text-slate-400 italic">
                                —
                              </td>
                            );
                          }
                          const isLowest = quoteEntry.is_lowest;
                          return (
                            <td
                              key={bid.quotationId}
                              className={`py-2.5 px-3 text-right font-mono ${
                                isLowest ? 'bg-emerald-50/25 font-bold text-emerald-800' : 'text-slate-900'
                              }`}
                            >
                              <div>{formatCurrency(quoteEntry.unit_price, currency)}</div>
                              {isLowest && (
                                <span className="text-[9px] px-1 rounded bg-emerald-100 text-emerald-800 font-bold">
                                  Lowest
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  : (rfq.items || []).map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-2.5 px-4 font-medium text-slate-900">
                          <div>{item.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            Target: {formatCurrency(item.targetUnitPrice || 0, currency)} / {item.unit}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          {(item.quantity ?? 0).toLocaleString()} {item.unit || ''}
                        </td>
                        {bids.map((bid) => {
                          const line = bid.lineItemsMap[item.id];
                          if (!line) {
                            return (
                              <td key={bid.quotationId} className="py-2.5 px-3 text-right text-slate-400 italic">
                                —
                              </td>
                            );
                          }
                          return (
                            <td
                              key={bid.quotationId}
                              className={`py-2.5 px-3 text-right font-mono ${
                                line.isLowestUnitPrice ? 'bg-emerald-50/25 font-bold text-emerald-800' : 'text-slate-900'
                              }`}
                            >
                              <div>{formatCurrency(line.unitPrice, currency)}</div>
                              {line.isLowestUnitPrice && (
                                <span className="text-[9px] px-1 rounded bg-emerald-100 text-emerald-800 font-bold">
                                  Lowest
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
