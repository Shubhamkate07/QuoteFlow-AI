import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { QuotationStatusBadge } from '../../features/quotations/components/QuotationStatusBadge';
import { QuotationDetailModal } from '../../features/quotations/components/QuotationDetailModal';
import { ReplaceDocumentModal } from '../../features/quotations/components/ReplaceDocumentModal';
import { DeleteQuotationModal } from '../../features/quotations/components/DeleteQuotationModal';
import { useQuotation } from '../../features/quotations/context/QuotationContext';
import type { Quotation } from '../../features/quotations/types';
import { formatCurrency, formatDate } from '../../utils/formatters';
import { ROUTES } from '../../routes/paths';
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  Search,
  Eye,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ArrowUpRight,
  FileSearch,
  AlertCircle,
  Paperclip,
} from 'lucide-react';

export const QuotationsPage: React.FC = () => {
  const { quotations, isLoading, error, deleteQuotation, refreshQuotations } = useQuotation();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modal inspection states
  const [detailQuotation, setDetailQuotation] = useState<Quotation | null>(null);
  const [replaceQuotation, setReplaceQuotation] = useState<Quotation | null>(null);
  const [deleteQuotationTarget, setDeleteQuotationTarget] = useState<Quotation | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Compute stats
  const totalCount = quotations.length;
  const completedCount = quotations.filter((q) => q.status === 'completed').length;
  const reviewCount = quotations.filter((q) => q.status === 'needs_review').length;
  const inProgressCount = quotations.filter(
    (q) => q.status === 'processing' || q.status === 'uploaded'
  ).length;

  // Filter list
  const filteredQuotations = quotations.filter((q) => {
    const matchesSearch =
      q.supplierName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.quoteReference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.rfqNumber.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'completed' && q.status === 'completed') ||
      (statusFilter === 'needs_review' && q.status === 'needs_review') ||
      (statusFilter === 'processing' && (q.status === 'processing' || q.status === 'uploaded')) ||
      (statusFilter === 'failed' && q.status === 'failed');

    return matchesSearch && matchesStatus;
  });

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
    <PageContainer>
      <PageHeader
        breadcrumbs={[{ label: 'Quotations' }]}
        title="Quotation Management"
        description="Monitor multi-format vendor quotations, inspect uploaded documents, and track line items."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refreshQuotations()}
              disabled={isLoading}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Link to={ROUTES.RFQS}>
              <Button variant="primary" size="sm" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
                View RFQ Packages
              </Button>
            </Link>
          </div>
        }
      />

      {/* Backend Error Banner */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => refreshQuotations()}>
            Try Again
          </Button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Quotations
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Across active RFQs</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
                Verified
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{completedCount}</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Ready for comparison</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-amber-700 uppercase tracking-wider">
                Needs Review
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{reviewCount}</h3>
              <p className="text-[11px] text-amber-600/80 mt-0.5">Spec variances detected</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-sky-600 uppercase tracking-wider">
                Processing / Queued
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{inProgressCount}</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Document uploads</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <Input
                placeholder="Search by supplier, quote ref, file name, or RFQ number..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftIcon={<Search className="w-4 h-4 text-slate-400" />}
              />
            </div>
            <div className="w-full sm:w-56">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: 'all', label: 'All Statuses' },
                  { value: 'completed', label: 'Completed (Verified)' },
                  { value: 'needs_review', label: 'Needs Review' },
                  { value: 'processing', label: 'Processing / Ingesting' },
                  { value: 'failed', label: 'Extraction Failed' },
                ]}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quotations Master Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading && quotations.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
              <p className="text-xs font-semibold text-slate-700">Loading quotations from backend...</p>
            </div>
          ) : filteredQuotations.length === 0 ? (
            <div className="p-12 text-center">
              <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <h4 className="text-sm font-semibold text-slate-800">
                {quotations.length === 0 ? 'No quotations uploaded yet' : 'No quotations match your criteria'}
              </h4>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                {quotations.length === 0
                  ? 'Open an RFQ and upload supplier documents (PDF, Excel, Images) to start.'
                  : 'Try adjusting your search terms or clearing the status filter.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50/75 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">RFQ Number</th>
                    <th className="py-3 px-4">Supplier & Reference</th>
                    <th className="py-3 px-3">Document Source</th>
                    <th className="py-3 px-3">Extraction Status</th>
                    <th className="py-3 px-3 text-right">Quoted Amount</th>
                    <th className="py-3 px-3">Lead Time & Terms</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredQuotations.map((quote) => (
                    <tr key={quote.id} className="hover:bg-slate-50/70 transition-colors">
                      {/* RFQ Reference */}
                      <td className="py-3.5 px-4">
                        <Link
                          to={`/rfqs/${quote.rfqId}`}
                          className="font-mono font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
                        >
                          {quote.rfqNumber}
                        </Link>
                      </td>

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
                          <div className="min-w-0 max-w-[170px]">
                            <span className="block truncate font-mono text-[11px] text-slate-700" title={quote.fileName}>
                              {quote.fileName}
                            </span>
                            <div className="flex items-center space-x-1.5 text-[10px] text-slate-400">
                              <span>{quote.fileSize}</span>
                              {quote.documents && quote.documents.length > 1 && (
                                <span className="inline-flex items-center text-indigo-600 font-medium">
                                  <Paperclip className="w-2.5 h-2.5 mr-0.5" />
                                  {quote.documents.length} files
                                </span>
                              )}
                            </div>
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
                            {quote.status === 'failed' ? 'Failed' : `${quote.currency} 0.00`}
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
                            title="Inspect Documents & Extracted Details"
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

      {/* Inspect Extraction & Documents Detail Modal */}
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
    </PageContainer>
  );
};
