import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import { QuotationStatusBadge } from './QuotationStatusBadge';
import { QuotationUploadModal } from './QuotationUploadModal';
import { ReplaceDocumentModal } from './ReplaceDocumentModal';
import { DeleteQuotationModal } from './DeleteQuotationModal';
import { QuotationDetailModal } from './QuotationDetailModal';
import { useQuotation } from '../context/QuotationContext';
import type { Quotation } from '../types';
import type { RfqItem } from '../../rfq/types';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import { ROUTES } from '../../../routes/paths';
import {
  UploadCloud,
  FileText,
  FileSpreadsheet,
  FileImage,
  Eye,
  RefreshCw,
  Trash2,
  FileCheck2,
  AlertTriangle,
  Clock,
  FileSearch,
} from 'lucide-react';

interface QuotationManagementSectionProps {
  rfqId: string;
  rfqCurrency: string;
  rfqItems: RfqItem[];
  invitedSupplierIds?: string[];
}

export const QuotationManagementSection: React.FC<QuotationManagementSectionProps> = ({
  rfqId,
  rfqCurrency,
  rfqItems,
  invitedSupplierIds = [],
}) => {
  const { getQuotationsByRfq, deleteQuotation } = useQuotation();
  const quotations = getQuotationsByRfq(rfqId);

  // Modal states
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [detailQuotation, setDetailQuotation] = useState<Quotation | null>(null);
  const [replaceQuotation, setReplaceQuotation] = useState<Quotation | null>(null);
  const [deleteQuotationTarget, setDeleteQuotationTarget] = useState<Quotation | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Status Filter tab
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredQuotes = quotations.filter((q) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'completed') return q.status === 'completed';
    if (statusFilter === 'needs_review') return q.status === 'needs_review';
    if (statusFilter === 'processing') return q.status === 'processing' || q.status === 'uploaded';
    if (statusFilter === 'failed') return q.status === 'failed';
    return true;
  });

  const completedCount = quotations.filter((q) => q.status === 'completed').length;
  const needsReviewCount = quotations.filter((q) => q.status === 'needs_review').length;
  const inProgressCount = quotations.filter((q) => q.status === 'processing' || q.status === 'uploaded').length;

  const handleDeleteConfirm = async () => {
    if (!deleteQuotationTarget) return;
    try {
      setIsDeleting(true);
      await deleteQuotation(deleteQuotationTarget.id);
      setDeleteQuotationTarget(null);
    } catch (err) {
      console.error('Failed to delete quotation:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'excel':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-600" />;
      case 'image':
        return <FileImage className="w-4 h-4 text-amber-600" />;
      default:
        return <FileText className="w-4 h-4 text-rose-600" />;
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <CardTitle>Supplier Quotations</CardTitle>
                <Badge variant="neutral" size="sm">
                  {quotations.length} Bids
                </Badge>
              </div>
              <CardDescription>
                Ingest PDF, Excel, or scanned bids for automated line-item parsing and spec matching
              </CardDescription>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsUploadOpen(true)}
              leftIcon={<UploadCloud className="w-4 h-4" />}
            >
              Upload Quotation
            </Button>
          </div>

          {/* Quick Metrics & Filter Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-1.5 text-xs">
              <button
                type="button"
                onClick={() => setStatusFilter('all')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  statusFilter === 'all'
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                All ({quotations.length})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('completed')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors inline-flex items-center gap-1 ${
                  statusFilter === 'completed'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                }`}
              >
                <FileCheck2 className="w-3 h-3" />
                Completed ({completedCount})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('needs_review')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors inline-flex items-center gap-1 ${
                  statusFilter === 'needs_review'
                    ? 'bg-amber-600 text-white'
                    : 'bg-amber-50 text-amber-800 hover:bg-amber-100'
                }`}
              >
                <AlertTriangle className="w-3 h-3" />
                Needs Review ({needsReviewCount})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('processing')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors inline-flex items-center gap-1 ${
                  statusFilter === 'processing'
                    ? 'bg-sky-600 text-white'
                    : 'bg-sky-50 text-sky-700 hover:bg-sky-100'
                }`}
              >
                <Clock className="w-3 h-3" />
                Processing ({inProgressCount})
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {filteredQuotes.length === 0 ? (
            <div className="p-10 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-800">
                  No supplier quotations found
                </h4>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  {statusFilter === 'all'
                    ? 'Upload vendor PDF invoices, Excel quote sheets, or scanned faxes to begin AI extraction.'
                    : `No quotations match the filter "${statusFilter}".`}
                </p>
              </div>
              {statusFilter === 'all' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsUploadOpen(true)}
                  leftIcon={<UploadCloud className="w-4 h-4" />}
                >
                  Upload First Quotation
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50/75 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Supplier & Ref</th>
                    <th className="py-3 px-3">Document Source</th>
                    <th className="py-3 px-3">Extraction Status</th>
                    <th className="py-3 px-3 text-right">Quoted Amount</th>
                    <th className="py-3 px-3">Lead Time & Terms</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredQuotes.map((quote) => (
                    <tr key={quote.id} className="hover:bg-slate-50/70 transition-colors">
                      {/* Supplier & Reference */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900 text-xs">
                          {quote.supplierName}
                        </div>
                        <div className="flex items-center space-x-2 text-[11px] text-slate-500 mt-0.5">
                          <span className="font-mono">{quote.quoteReference}</span>
                          <span>•</span>
                          <span>{formatDate(quote.uploadedAt)}</span>
                        </div>
                      </td>

                      {/* Document Source */}
                      <td className="py-3.5 px-3">
                        <div className="flex items-center space-x-2">
                          {getFileIcon(quote.fileType)}
                          <div className="min-w-0 max-w-[160px]">
                            <span className="block truncate font-mono text-[11px] text-slate-700" title={quote.fileName}>
                              {quote.fileName}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {quote.fileSize}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Extraction Status */}
                      <td className="py-3.5 px-3">
                        <div className="space-y-1">
                          <QuotationStatusBadge
                            status={quote.status}
                            progress={quote.processingProgress}
                            size="sm"
                          />
                          {quote.status === 'processing' && (
                            <div className="w-24 bg-slate-100 rounded-full h-1 overflow-hidden">
                              <div
                                className="bg-sky-500 h-full transition-all duration-500"
                                style={{ width: `${quote.processingProgress}%` }}
                              />
                            </div>
                          )}
                          {quote.status === 'needs_review' && (
                            <span className="block text-[10px] text-amber-700 font-medium truncate max-w-[140px]" title={quote.reviewNotes}>
                              Spec variance flagged
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Quoted Amount */}
                      <td className="py-3.5 px-3 text-right">
                        {quote.totalAmount > 0 ? (
                          <div className="font-bold font-mono text-slate-900 text-xs">
                            {formatCurrency(quote.totalAmount, quote.currency)}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400 italic">
                            {quote.status === 'failed' ? 'Failed' : 'Extracting...'}
                          </span>
                        )}
                        {quote.extractedItems.length > 0 && (
                          <span className="text-[10px] text-slate-400 block">
                            {quote.extractedItems.length} line items
                          </span>
                        )}
                      </td>

                      {/* Lead Time & Terms */}
                      <td className="py-3.5 px-3">
                        <div className="text-slate-700 text-[11px]">
                          {quote.commercialTerms.deliveryLeadWeeks > 0 ? (
                            <span>{quote.commercialTerms.deliveryLeadWeeks} weeks lead</span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 truncate max-w-[130px]" title={quote.commercialTerms.incoterms}>
                          {quote.commercialTerms.incoterms || 'Terms pending'}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-1">
                          <Link
                            to={ROUTES.QUOTATION_REVIEW(quote.id)}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                            title="Review & Verify AI Extraction"
                          >
                            <FileSearch className="w-4 h-4 text-indigo-600" />
                          </Link>

                          <button
                            type="button"
                            onClick={() => setDetailQuotation(quote)}
                            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
                            title="Inspect Extracted Quotation Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => setReplaceQuotation(quote)}
                            className="p-1.5 text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded-md transition-colors"
                            title="Replace Document"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => setDeleteQuotationTarget(quote)}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                            title="Delete Quotation"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Quotation Modal */}
      <QuotationUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        rfqId={rfqId}
        rfqCurrency={rfqCurrency}
        rfqItems={rfqItems}
        invitedSupplierIds={invitedSupplierIds}
      />

      {/* Inspect Extraction Detail Modal */}
      <QuotationDetailModal
        isOpen={!!detailQuotation}
        onClose={() => setDetailQuotation(null)}
        quotation={detailQuotation}
        onReplaceDocument={(q) => setReplaceQuotation(q)}
      />

      {/* Replace Document Modal */}
      <ReplaceDocumentModal
        isOpen={!!replaceQuotation}
        onClose={() => setReplaceQuotation(null)}
        quotation={replaceQuotation}
      />

      {/* Delete Quotation Modal */}
      <DeleteQuotationModal
        isOpen={!!deleteQuotationTarget}
        onClose={() => setDeleteQuotationTarget(null)}
        quotation={deleteQuotationTarget}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </>
  );
};
