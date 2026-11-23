import React from 'react';
import { Card, CardContent } from '../../../components/ui/Card';
import { formatCurrency } from '../../../utils/formatters';
import type { BackendPriceComparisonData } from '../types';
import type { Rfq } from '../../rfq/types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  Split,
  FileSpreadsheet,
} from 'lucide-react';

interface PriceComparisonViewProps {
  rfq: Rfq;
  priceData?: BackendPriceComparisonData;
}

export const PriceComparisonView: React.FC<PriceComparisonViewProps> = ({
  rfq,
  priceData,
}) => {
  if (!priceData || !priceData.quotations || priceData.quotations.length === 0) {
    return (
      <Card className="p-12 text-center text-slate-500">
        <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-800">No Price Comparison Data Available</h4>
        <p className="text-xs text-slate-400 mt-1">
          Generate comparison to compute item-by-item pricing metrics.
        </p>
      </Card>
    );
  }

  const currency = priceData.comparison_currency || rfq.currency || 'USD';

  return (
    <div className="space-y-6">
      {/* Financial Comparison Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-emerald-200 bg-emerald-50/15">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider">
                Lowest Overall Bid
              </span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-700">
              {priceData.lowest_grand_total != null
                ? formatCurrency(priceData.lowest_grand_total, currency)
                : '—'}
            </div>
            <span className="text-xs text-emerald-700 mt-0.5 block font-medium">
              Single-vendor lowest total
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Highest Quoted Bid
              </span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-900">
              {priceData.highest_grand_total != null
                ? formatCurrency(priceData.highest_grand_total, currency)
                : '—'}
            </div>
            <span className="text-xs text-slate-400 mt-0.5 block">
              Market upper bound
            </span>
          </CardContent>
        </Card>

        <Card className="border-indigo-200 bg-indigo-50/15">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-indigo-800 uppercase tracking-wider">
                Single-Source Savings
              </span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <div className="text-2xl font-bold font-mono text-indigo-700">
              {formatCurrency(priceData.max_savings_amount, currency)}
            </div>
            <span className="text-xs text-indigo-700 mt-0.5 block font-medium">
              {priceData.max_savings_percentage}% spread vs highest quote
            </span>
          </CardContent>
        </Card>

        <Card className="border-purple-200 bg-purple-50/15">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-purple-800 uppercase tracking-wider">
                Cherry-Pick Optimal
              </span>
              <DataOriginBadge type="calculated" size="xs" />
            </div>
            <div className="text-2xl font-bold font-mono text-purple-900">
              {formatCurrency(priceData.cherry_pick_total, currency)}
            </div>
            <span className="text-xs text-purple-700 mt-0.5 block font-medium flex items-center gap-1">
              <Split className="w-3.5 h-3.5" />
              Saves additional {formatCurrency(priceData.cherry_pick_savings, currency)}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Supplier Total Quotation Comparison Table */}
      <Card className="overflow-hidden border border-slate-200">
        <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold text-slate-900">Supplier Financial Totals & Variances</h4>
            <span className="text-[11px] text-slate-400">
              Deterministic line price arithmetic across all eligible bidders
            </span>
          </div>
          <DataOriginBadge type="calculated" size="xs" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-sans">
              <tr>
                <th className="py-2.5 px-3">Supplier</th>
                <th className="py-2.5 px-3 text-right">Subtotal</th>
                <th className="py-2.5 px-3 text-right">Taxes</th>
                <th className="py-2.5 px-3 text-right">Shipping</th>
                <th className="py-2.5 px-3 text-right">Grand Total</th>
                <th className="py-2.5 px-3 text-right">Difference vs Lowest</th>
                <th className="py-2.5 px-3 text-right">% Variance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {priceData.quotations.map((q) => (
                <tr
                  key={q.quotation_id}
                  className={q.is_lowest_price ? 'bg-emerald-50/25 font-semibold' : ''}
                >
                  <td className="py-3 px-3 font-sans font-medium text-slate-900">
                    <div className="flex items-center gap-2">
                      <span>{q.supplier_name}</span>
                      {q.is_lowest_price && (
                        <span className="px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[9px] font-bold">
                          Lowest Price
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">Ref: {q.quotation_number}</span>
                  </td>
                  <td className="py-3 px-3 text-right text-slate-700">
                    {q.subtotal != null ? formatCurrency(q.subtotal, currency) : '—'}
                  </td>
                  <td className="py-3 px-3 text-right text-slate-500">
                    {q.tax_amount != null ? formatCurrency(q.tax_amount, currency) : '0'}
                  </td>
                  <td className="py-3 px-3 text-right text-slate-500">
                    {q.shipping_amount != null ? formatCurrency(q.shipping_amount, currency) : '0'}
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-slate-900 text-sm">
                    {formatCurrency(q.grand_total, currency)}
                  </td>
                  <td className="py-3 px-3 text-right">
                    {q.price_difference_from_lowest === 0 || q.is_lowest_price ? (
                      <span className="text-emerald-700 font-bold">Baseline</span>
                    ) : (
                      <span className="text-slate-700">
                        +{formatCurrency(q.price_difference_from_lowest || 0, currency)}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-right">
                    {q.percentage_difference_from_lowest === 0 || q.is_lowest_price ? (
                      <span className="text-emerald-700 font-bold">0.0%</span>
                    ) : (
                      <span className="text-rose-600 font-semibold">
                        +{q.percentage_difference_from_lowest?.toFixed(1)}%
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Item-by-Item BOM Sourcing Matrix */}
      <Card className="overflow-hidden border border-slate-200">
        <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold text-slate-900">Line Items BOM Unit Price Matrix</h4>
            <span className="text-[11px] text-slate-400">
              Compare quoted unit prices across every RFQ requirement to spot cherry-pick savings
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <DataOriginBadge type="extracted" size="xs" label="Quoted Unit" />
            <DataOriginBadge type="calculated" size="xs" label="Lowest Highlight" />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-sans">
              <tr>
                <th className="py-2.5 px-3">Item Name</th>
                <th className="py-2.5 px-2 text-right">Qty</th>
                <th className="py-2.5 px-2">Unit</th>
                <th className="py-2.5 px-3 text-right">Lowest Quoted Unit</th>
                {priceData.quotations.map((q) => (
                  <th key={q.quotation_id} className="py-2.5 px-3 text-right">
                    {q.supplier_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {priceData.items_matrix.map((row) => (
                <tr key={row.rfq_item_id}>
                  <td className="py-3 px-3 font-sans font-medium text-slate-900">
                    <div>{row.item_name}</div>
                    {row.target_unit_price != null && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        Target: {formatCurrency(row.target_unit_price, currency)}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-2 text-right text-slate-700">{row.quantity}</td>
                  <td className="py-3 px-2 text-slate-500 font-sans">{row.uom}</td>
                  <td className="py-3 px-3 text-right text-emerald-700 font-bold bg-emerald-50/30">
                    {row.lowest_unit_price != null
                      ? formatCurrency(row.lowest_unit_price, currency)
                      : '—'}
                  </td>
                  {priceData.quotations.map((q) => {
                    const quoteEntry = row.quotes?.find(
                      (quote) => quote.quotation_id === q.quotation_id
                    );
                    if (!quoteEntry) {
                      return (
                        <td key={q.quotation_id} className="py-3 px-3 text-right text-slate-300 italic">
                          —
                        </td>
                      );
                    }
                    return (
                      <td
                        key={q.quotation_id}
                        className={`py-3 px-3 text-right ${
                          quoteEntry.is_lowest
                            ? 'bg-emerald-50/30 font-bold text-emerald-800'
                            : 'text-slate-800'
                        }`}
                      >
                        <div>{formatCurrency(quoteEntry.unit_price, currency)}</div>
                        <span className="text-[10px] text-slate-400 block font-normal">
                          Ext: {formatCurrency(quoteEntry.extended_price, currency)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
