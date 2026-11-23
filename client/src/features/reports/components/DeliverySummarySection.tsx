import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import type { ComparisonSupplierBid } from '../../comparison/types';
import type { Rfq } from '../../rfq/types';
import { formatDate } from '../../../utils/formatters';
import { Truck, CheckCircle2, Clock } from 'lucide-react';

interface DeliverySummarySectionProps {
  rfq: Rfq;
  bids: ComparisonSupplierBid[];
}

export const DeliverySummarySection: React.FC<DeliverySummarySectionProps> = ({
  rfq,
  bids,
}) => {
  return (
    <Card className="mb-6 border-slate-200 shadow-xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Truck className="w-4 h-4 text-sky-600" />
            <CardTitle>4. Delivery Timeline & Logistics Summary</CardTitle>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">
            RFQ Deadline: {formatDate(rfq.requiredDeliveryDate)}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {bids.map((bid) => {
            const isOnTime =
              bid.onTimeStatus?.toLowerCase().includes('schedule') ||
              bid.onTimeStatus?.toLowerCase().includes('on_time') ||
              bid.deliveryLeadWeeks <= 4;
            return (
              <div
                key={bid.quotationId}
                className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-900 truncate max-w-[170px]" title={bid.supplierName}>
                    {bid.supplierName}
                  </h4>
                  {isOnTime ? (
                    <Badge variant="success" size="sm">
                      <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                      On Schedule
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm">
                      <Clock className="w-3 h-3 mr-1 inline" />
                      Delivery Delayed
                    </Badge>
                  )}
                </div>

                <div className="space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-sans">Quoted Lead Time:</span>
                    <span className="font-bold text-slate-900">{bid.deliveryLeadWeeks} Calendar Weeks</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-sans">Incoterms Standard:</span>
                    <span className="font-semibold text-slate-800">{bid.incoterms || 'DAP'}</span>
                  </div>
                </div>

                {/* Logistics Burden Breakdown */}
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-[11px] text-slate-600">
                  {bid.incoterms?.toLowerCase().includes('dap') ? (
                    <p className="text-emerald-800">
                      <strong>DAP Destination:</strong> Supplier arranges freight logistics, export clearance, and delivers to facility door.
                    </p>
                  ) : bid.incoterms?.toLowerCase().includes('fob') ? (
                    <p className="text-slate-700">
                      <strong>FOB Origin:</strong> Supplier clears origin port; buyer manages freight forwarding and in-transit insurance.
                    </p>
                  ) : (
                    <p className="text-amber-800">
                      <strong>EXW Origin:</strong> Buyer assumes full pickup freight coordination, freight costs, and import/export filings.
                    </p>
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
