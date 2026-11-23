import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../../components/ui/Table';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/feedback/EmptyState';
import { Eye, FileSpreadsheet } from 'lucide-react';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import type { RecentRfq } from '../types';
import { ROUTES } from '../../../routes/paths';

interface RecentRfqsTableProps {
  rfqs: RecentRfq[];
  onCreateRfq: () => void;
}

export const RecentRfqsTable: React.FC<RecentRfqsTableProps> = ({ rfqs, onCreateRfq }) => {
  const [filter, setFilter] = useState<'all' | 'under_review' | 'open' | 'completed'>('all');

  const filteredRfqs = rfqs.filter((r) => {
    if (filter === 'all') return true;
    return r.status === filter;
  });

  const statusConfig = {
    under_review: { label: 'Under Review', variant: 'warning' as const },
    open: { label: 'Awaiting Bids', variant: 'neutral' as const },
    completed: { label: 'Completed', variant: 'success' as const },
    draft: { label: 'Draft', variant: 'neutral' as const },
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle>Recent RFQ Packages</CardTitle>
            <CardDescription>
              Manufacturing requisitions, incoming quote responses, and target vs lowest bids
            </CardDescription>
          </div>

          <div className="flex items-center gap-1.5 self-start sm:self-auto">
            {(['all', 'under_review', 'open', 'completed'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setFilter(tab)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  filter === tab
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {tab === 'all'
                  ? 'All'
                  : tab === 'under_review'
                  ? 'In Review'
                  : tab === 'open'
                  ? 'Open'
                  : 'Completed'}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {filteredRfqs.length === 0 ? (
          <EmptyState
            icon={FileSpreadsheet}
            title="No RFQs found in this category"
            description="Create a new requisition to invite suppliers and start comparing quotations."
            actionLabel="Create RFQ"
            onAction={onCreateRfq}
            className="m-6"
          />
        ) : (
          <Table className="min-w-[760px]">
            <TableHeader>
              <TableRow>
                <TableHead className="w-28 whitespace-nowrap">RFQ Reference</TableHead>
                <TableHead className="min-w-[160px]">Scope & Category</TableHead>
                <TableHead className="w-24 whitespace-nowrap">Quotes</TableHead>
                <TableHead className="w-28 whitespace-nowrap">Baseline Spend</TableHead>
                <TableHead className="w-28 whitespace-nowrap">Lowest Bid</TableHead>
                <TableHead className="w-24 whitespace-nowrap">Deadline</TableHead>
                <TableHead className="w-28 whitespace-nowrap">Status</TableHead>
                <TableHead className="w-20 text-right whitespace-nowrap pr-3">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRfqs.map((rfq) => {
                const status = statusConfig[rfq.status] || {
                  label: rfq.status,
                  variant: 'neutral' as const,
                };
                const savings = rfq.lowestQuote ? rfq.targetBaseline - rfq.lowestQuote : 0;

                return (
                  <TableRow key={rfq.id}>
                    <TableCell className="font-mono text-xs font-semibold text-slate-900">
                      {rfq.code}
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-slate-800 leading-snug">{rfq.title}</div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {rfq.category} • {rfq.itemsCount} required items
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs">
                        <span className="font-semibold text-slate-800">{rfq.quotesReceived}</span>
                        <span className="text-slate-400"> of {rfq.quotesInvited} bids</span>
                      </div>
                      <div className="w-16 bg-slate-100 h-1 rounded-full mt-1 overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full"
                          style={{
                            width: `${(rfq.quotesReceived / rfq.quotesInvited) * 100}%`,
                          }}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-700 font-medium">
                      {formatCurrency(rfq.targetBaseline)}
                    </TableCell>
                    <TableCell>
                      {rfq.lowestQuote ? (
                        <div>
                          <div className="font-semibold text-slate-900">
                            {formatCurrency(rfq.lowestQuote)}
                          </div>
                          {savings > 0 && (
                            <div className="text-[11px] font-semibold text-emerald-600">
                              Save {formatCurrency(savings)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400 italic">Awaiting quotes</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatDate(rfq.deadline)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={status.variant} dot size="sm">
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap pr-3">
                      <Link to={ROUTES.RFQ_DETAIL(rfq.id)}>
                        <Button
                          variant="ghost"
                          size="sm"
                          leftIcon={<Eye className="w-3.5 h-3.5" />}
                        >
                          View
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};
