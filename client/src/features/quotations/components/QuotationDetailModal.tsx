import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import { QuotationStatusBadge } from './QuotationStatusBadge';
import type { Quotation, QuotationDocument } from '../types';
import { quotationService } from '../services/quotationService';
import { useQuotation } from '../context/QuotationContext';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import { ROUTES } from '../../../routes/paths';
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  Calendar,
  Truck,
  ShieldCheck,
  CreditCard,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Layers,
  FileCheck2,
  FileSearch,
  Download,
  ExternalLink,
  Trash2,
  Paperclip,
  CheckCircle2,
  Clock,
} from 'lucide-react';

interface QuotationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  quotation: Quotation | null;
  onReplaceDocument?: (quotation: Quotation) => void;
}

export const QuotationDetailModal: React.FC<QuotationDetailModalProps> = ({
  isOpen,
  onClose,
  quotation,
  onReplaceDocument,
}) => {
  const { deleteDocument } = useQuotation();
  const [activeTab, setActiveTab] = useState<'documents' | 'line_items' | 'commercial_terms'>('documents');
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [docActionError, setDocActionError] = useState<string | null>(null);

  if (!quotation) return null;

  const getFileIcon = (fileName?: string, fileType?: string) => {
    const ext = fileName?.split('.').pop()?.toLowerCase() || '';
    if (ext === 'xlsx' || ext === 'xls' || ext === 'csv' || fileType === 'excel') {
      return <FileSpreadsheet className="w-5 h-5 text-emerald-600" />;
    }
    if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || fileType === 'image') {
      return <FileImage className="w-5 h-5 text-amber-600" />;
    }
    return <FileText className="w-5 h-5 text-rose-600" />;
  };

  const handleDownload = async (doc: QuotationDocument, inline: boolean) => {
    // If opening inline in browser, open blank window immediately to preserve user gesture context
    let previewWindow: Window | null = null;
    if (inline) {
      try {
        previewWindow = window.open('about:blank', '_blank');
      } catch {
        previewWindow = null;
      }
    }

    try {
      setDocActionError(null);
      setDownloadingDocId(doc.id);
      const { blob, filename } = await quotationService.downloadDocumentBlob(doc.id, inline);
      const url = window.URL.createObjectURL(blob);
      if (inline) {
        if (previewWindow && !previewWindow.closed) {
          previewWindow.location.href = url;
        } else {
          window.open(url, '_blank');
        }
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = doc.originalFilename || filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
    } catch (err: unknown) {
      if (previewWindow && !previewWindow.closed) {
        previewWindow.close();
      }
      let message = 'Failed to download document';
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: unknown; status?: number } };
        if (axiosErr.response?.data instanceof Blob) {
          try {
            const text = await axiosErr.response.data.text();
            const parsed = JSON.parse(text);
            message = parsed.detail || parsed.message || message;
          } catch {
            message = `HTTP ${axiosErr.response?.status || 500} error downloading document`;
          }
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      setDocActionError(`Download error: ${message}`);
    } finally {
      setDownloadingDocId(null);
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!window.confirm('Are you sure you want to delete this uploaded document?')) {
      return;
    }
    try {
      setDocActionError(null);
      setDeletingDocId(docId);
      await deleteDocument(docId, quotation.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete document';
      setDocActionError(`Delete error: ${message}`);
    } finally {
      setDeletingDocId(null);
    }
  };

  const getDocStatusBadge = (status: QuotationDocument['processingStatus']) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="success" size="sm" className="inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Ready
          </Badge>
        );
      case 'processing':
        return (
          <Badge variant="info" size="sm" className="inline-flex items-center gap-1">
            <RefreshCw className="w-3 h-3 animate-spin" /> Processing
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="danger" size="sm" className="inline-flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Failed
          </Badge>
        );
      case 'pending':
      default:
        return (
          <Badge variant="neutral" size="sm" className="inline-flex items-center gap-1">
            <Clock className="w-3 h-3" /> Queued
          </Badge>
        );
    }
  };

  const documents = quotation.documents || [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Quotation: ${quotation.supplierName}`}
      description={`Reference: ${quotation.quoteReference} • RFQ: ${quotation.rfqNumber}`}
      maxWidth="4xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2 text-xs text-slate-500">
            <span className="font-medium text-slate-700">Primary Source:</span>
            <span className="font-mono text-slate-600">{quotation.fileName}</span>
            <span>({quotation.fileSize})</span>
          </div>

          <div className="flex items-center gap-2">
            <Link to={ROUTES.QUOTATION_REVIEW(quotation.id)}>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<FileSearch className="w-3.5 h-3.5 text-indigo-600" />}
              >
                Review & Edit
              </Button>
            </Link>

            {onReplaceDocument && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose();
                  onReplaceDocument(quotation);
                }}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Replace Document
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Top Status & Overview Banner */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-white rounded-lg border border-slate-200 shrink-0">
              {getFileIcon(quotation.fileName, quotation.fileType)}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h4 className="font-semibold text-sm text-slate-900">
                  {quotation.supplierName}
                </h4>
                <QuotationStatusBadge status={quotation.status} progress={quotation.processingProgress} size="sm" />
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Uploaded {formatDate(quotation.uploadedAt)} • Ref: <span className="font-mono font-medium text-slate-700">{quotation.quoteReference}</span>
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Total Quotation Value
            </span>
            <span className="text-lg font-bold text-slate-900 font-mono">
              {quotation.totalAmount > 0
                ? formatCurrency(quotation.totalAmount, quotation.currency)
                : `${quotation.currency} 0.00`}
            </span>
          </div>
        </div>

        {/* Action Error Alert */}
        {docActionError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <p>{docActionError}</p>
          </div>
        )}

        {/* AI Flag Alerts */}
        {quotation.status === 'needs_review' && quotation.reviewNotes && (
          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Review Alert: Specification Variance Detected</span>
              <p className="mt-0.5 text-amber-800 leading-relaxed">{quotation.reviewNotes}</p>
            </div>
          </div>
        )}

        {quotation.status === 'failed' && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-xs text-rose-900">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Document Ingestion Failed</span>
              <p className="mt-0.5 text-rose-800 leading-relaxed">
                {quotation.processingError || 'The uploaded file could not be parsed. Click "Replace Document" to upload a cleaner file or higher-resolution scan.'}
              </p>
            </div>
          </div>
        )}

        {/* Navigation Tabs: Documents vs Line Items vs Commercial Terms */}
        <div className="flex border-b border-slate-200 space-x-6 text-sm">
          <button
            type="button"
            onClick={() => setActiveTab('documents')}
            className={`pb-2.5 font-medium border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'documents'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Paperclip className="w-4 h-4" />
            <span>Uploaded Documents ({documents.length || 1})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('line_items')}
            className={`pb-2.5 font-medium border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'line_items'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Line Items ({quotation.extractedItems.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('commercial_terms')}
            className={`pb-2.5 font-medium border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === 'commercial_terms'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileCheck2 className="w-4 h-4" />
            <span>Commercial & Delivery Terms</span>
          </button>
        </div>

        {/* Tab 1: Uploaded Documents */}
        {activeTab === 'documents' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <p>Uploaded quotation source files for this bid. All files are securely stored and isolated by organization.</p>
              {onReplaceDocument && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    onClose();
                    onReplaceDocument(quotation);
                  }}
                  leftIcon={<RefreshCw className="w-3 h-3" />}
                >
                  Upload Replacement
                </Button>
              )}
            </div>

            {documents.length > 0 ? (
              <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 bg-white">
                {documents.map((doc) => {
                  const isDownloading = downloadingDocId === doc.id;
                  const isDeleting = deletingDocId === doc.id;

                  return (
                    <div
                      key={doc.id}
                      className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60 transition-colors"
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <div className="p-2 bg-slate-50 rounded-lg border border-slate-200 shrink-0">
                          {getFileIcon(doc.originalFilename, doc.fileType)}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-slate-900 truncate font-mono" title={doc.originalFilename}>
                            {doc.originalFilename}
                          </p>
                          <div className="flex items-center space-x-2 text-[11px] text-slate-500 mt-0.5">
                            <span>{doc.fileSizeDisplay}</span>
                            <span>•</span>
                            <span className="uppercase text-[10px] font-semibold tracking-wider text-slate-400">
                              {doc.fileExtension}
                            </span>
                            <span>•</span>
                            <span>Uploaded {formatDate(doc.createdAt)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
                        {getDocStatusBadge(doc.processingStatus)}

                        {/* View Inline Button */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(doc, true)}
                          disabled={isDownloading || isDeleting}
                          leftIcon={<ExternalLink className="w-3.5 h-3.5 text-indigo-600" />}
                          title="Open document in new browser tab"
                        >
                          View
                        </Button>

                        {/* Download File Button */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(doc, false)}
                          disabled={isDownloading || isDeleting}
                          leftIcon={<Download className="w-3.5 h-3.5 text-slate-600" />}
                          title="Download document to computer"
                        >
                          {isDownloading ? 'Downloading...' : 'Download'}
                        </Button>

                        {/* Delete Document Button */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteDoc(doc.id)}
                          disabled={isDownloading || isDeleting}
                          className="hover:border-rose-300 hover:bg-rose-50 text-slate-500 hover:text-rose-600"
                          title="Delete this document file"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-6 text-center bg-slate-50 rounded-xl border border-slate-200">
                <Paperclip className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">Primary file: {quotation.fileName}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Size: {quotation.fileSize}</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Line Items */}
        {activeTab === 'line_items' && (
          <div className="space-y-4">
            {quotation.extractedItems.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200">
                <Sparkles className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">
                  {quotation.status === 'processing'
                    ? 'AI Document extraction is currently processing...'
                    : quotation.status === 'failed'
                    ? 'No items extracted due to OCR or parsing error.'
                    : 'Quotation document uploaded. Line items will appear here once extracted or added.'}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Line items and pricing tables can also be reviewed and edited in the Review page.
                </p>
              </div>
            ) : (
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="py-2.5 px-4">Quoted Part & Description</th>
                        <th className="py-2.5 px-3 text-right">Quantity</th>
                        <th className="py-2.5 px-3 text-right">Unit Price</th>
                        <th className="py-2.5 px-3 text-right">Total ({quotation.currency})</th>
                        <th className="py-2.5 px-3 text-center">Confidence</th>
                        <th className="py-2.5 px-3 text-center">Spec Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {quotation.extractedItems.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-4 max-w-xs">
                            <div className="font-semibold text-slate-900 text-xs">
                              {item.extractedPartName}
                            </div>
                            <div className="text-[11px] text-slate-500 mt-0.5 leading-tight">
                              {item.materialSpec}
                            </div>
                            {item.discrepancyNote && (
                              <div className="mt-1.5 p-1.5 bg-amber-50 rounded border border-amber-200 text-[10px] text-amber-800 font-medium">
                                ⚠ {item.discrepancyNote}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-slate-700">
                            {item.extractedQuantity} {item.extractedUnit}
                          </td>
                          <td className="py-3 px-3 text-right font-mono font-medium text-slate-900">
                            {formatCurrency(item.unitPrice, quotation.currency)}
                          </td>
                          <td className="py-3 px-3 text-right font-mono font-bold text-slate-900">
                            {formatCurrency(item.totalPrice, quotation.currency)}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <div className="inline-flex items-center gap-1">
                              <span className="font-mono text-[11px] font-semibold text-slate-700">
                                {Math.round(item.confidenceScore * 100)}%
                              </span>
                              <div className="w-10 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    item.confidenceScore > 0.95
                                      ? 'bg-emerald-500'
                                      : item.confidenceScore > 0.85
                                      ? 'bg-amber-500'
                                      : 'bg-rose-500'
                                  }`}
                                  style={{ width: `${item.confidenceScore * 100}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-center">
                            {item.status === 'matched' ? (
                              <Badge variant="success" size="sm">
                                Matched
                              </Badge>
                            ) : item.status === 'variance' ? (
                              <Badge variant="warning" size="sm">
                                Variance
                              </Badge>
                            ) : (
                              <Badge variant="neutral" size="sm">
                                Unmatched
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Subtotal & Total Footer */}
                <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-end gap-6 text-xs">
                  <div>
                    <span className="text-slate-500 mr-2">Extracted Items Total:</span>
                    <span className="font-bold font-mono text-slate-900">
                      {formatCurrency(quotation.subtotal, quotation.currency)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 mr-2">Grand Total:</span>
                    <span className="font-extrabold font-mono text-slate-950">
                      {formatCurrency(quotation.totalAmount, quotation.currency)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Commercial & Legal Terms */}
        {activeTab === 'commercial_terms' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Payment Terms</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.paymentTerms || 'Not specified'}
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <Truck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Delivery Lead Time</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.deliveryLeadWeeks > 0
                  ? `${quotation.commercialTerms.deliveryLeadWeeks} Calendar Weeks`
                  : 'Pending extraction'}
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <Truck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Incoterms 2020</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.incoterms || 'Not specified'}
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Validity Period</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.validUntil
                  ? formatDate(quotation.commercialTerms.validUntil)
                  : 'Not specified'}
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Warranty & SLA</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.warrantyTerms || 'Not specified'}
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold uppercase tracking-wider text-[10px]">Tax Applicability</span>
              </div>
              <p className="text-xs font-semibold text-slate-900">
                {quotation.commercialTerms.taxesApplicable || 'Excluded / Standard'}
              </p>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
