import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { DocumentViewer } from '../../features/quotations/components/review/DocumentViewer';
import { ConfidenceScoreMeter } from '../../features/quotations/components/review/ConfidenceScoreMeter';
import { ValidationFlagsCard } from '../../features/quotations/components/review/ValidationFlagsCard';
import { ExtractionSupplierInfoCard } from '../../features/quotations/components/review/ExtractionSupplierInfoCard';
import { ExtractionQuotationInfoCard } from '../../features/quotations/components/review/ExtractionQuotationInfoCard';
import { ExtractionLineItemsEditor } from '../../features/quotations/components/review/ExtractionLineItemsEditor';
import { ExtractionFinancialsCard } from '../../features/quotations/components/review/ExtractionFinancialsCard';
import { ApproveExtractionModal } from '../../features/quotations/components/review/ApproveExtractionModal';
import { AuditHistoryModal } from '../../features/quotations/components/review/AuditHistoryModal';
import { DeleteQuotationModal } from '../../features/quotations/components/DeleteQuotationModal';
import { useQuotation } from '../../features/quotations/context/QuotationContext';
import { useAuth } from '../../features/auth/context/AuthContext';
import { quotationService } from '../../features/quotations/services/quotationService';
import { getErrorMessage } from '../../lib/api';
import {
  useExtraction,
  useExtractionsForQuotation,
  useSaveCorrections,
  useApproveExtraction,
  useRejectExtraction,
  useTriggerExtraction,
} from '../../features/quotations/hooks/useExtractionQueries';
import type {
  ExtractedSupplierData,
  ExtractedQuotationData,
  ExtractedCommercialTermsData,
  ExtractedLineItemData,
  FieldEvidence,
  BackendQuotationExtraction,
} from '../../features/quotations/types/extraction';
import { ROUTES } from '../../routes/paths';
import {
  ArrowLeft,
  Save,
  ShieldCheck,
  CheckCircle2,
  History,
  AlertTriangle,
  RotateCw,
  Loader2,
  Clock,
  Check,
  XCircle,
  Sparkles,
  Trash2,
} from 'lucide-react';

export const QuotationReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { getQuotationById, deleteQuotation, refreshQuotations } = useQuotation();
  // Direct quotation query fallback if context is not yet loaded (e.g. on direct browser refresh)
  const quotationDetailQuery = useQuery({
    queryKey: ['quotation', id],
    queryFn: () => quotationService.getQuotationById(id!),
    enabled: Boolean(id),
    staleTime: 30000,
    retry: 1,
  });

  const quotation = quotationDetailQuery.data || (id && !quotationDetailQuery.isError ? getQuotationById(id) : undefined);

  // Queries: try by extraction ID first, fallback to quotation's extractions
  const [localExtraction, setLocalExtraction] = useState<BackendQuotationExtraction | null>(null);
  const directExtractionQuery = useExtraction(localExtraction?.id || id);
  const quotationExtractionsQuery = useExtractionsForQuotation(quotation?.id || id);

  // Determine active extraction
  const extraction: BackendQuotationExtraction | undefined = useMemo(() => {
    // 1. Check if direct query has completed data
    if (directExtractionQuery.data && directExtractionQuery.data.status === 'completed') {
      return directExtractionQuery.data;
    }
    // 2. Check if quotation's extractions list has completed data
    const listMatch = quotationExtractionsQuery.data?.find(
      (e) => (localExtraction && e.id === localExtraction.id) || e.status === 'completed'
    ) || quotationExtractionsQuery.data?.[0];

    if (listMatch && listMatch.status === 'completed') {
      return listMatch;
    }

    if (localExtraction) return localExtraction;
    if (directExtractionQuery.data) return directExtractionQuery.data;
    if (listMatch) return listMatch;
    return undefined;
  }, [localExtraction, directExtractionQuery.data, quotationExtractionsQuery.data]);

  const isLoading = directExtractionQuery.isLoading || quotationExtractionsQuery.isLoading;

  // Mutations
  const saveCorrectionsMutation = useSaveCorrections();
  const approveExtractionMutation = useApproveExtraction();
  const rejectExtractionMutation = useRejectExtraction();
  const triggerExtractionMutation = useTriggerExtraction();

  // Local Editable State Buffer for Human Review
  const [supplier, setSupplier] = useState<ExtractedSupplierData>({});
  const [quotationData, setQuotationData] = useState<ExtractedQuotationData>({});
  const [commercialTerms, setCommercialTerms] = useState<ExtractedCommercialTermsData>({});
  const [lineItems, setLineItems] = useState<ExtractedLineItemData[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [saveWarningMessage, setSaveWarningMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);

  // User RBAC permissions for review and approve actions
  const { activeOrganization } = useAuth();
  const userRole = activeOrganization?.role;
  const canApprove = userRole === 'owner' || userRole === 'admin' || userRole === 'procurement_manager';
  const canReject = userRole === 'owner' || userRole === 'admin' || userRole === 'procurement_manager' || userRole === 'procurement_user';

  // Evidence Citation highlighting & Document Viewer coordination
  const [selectedEvidenceSnippet, setSelectedEvidenceSnippet] = useState<{
    page?: number;
    text?: string;
    fieldName?: string;
  } | null>(null);

  // Modals state
  const [isApproveModalOpen, setIsApproveModalOpen] = useState<boolean>(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteQuotation = async () => {
    const targetId = quotation?.id || extraction?.quotation_id || id;
    if (!targetId) return;
    try {
      setIsDeleting(true);
      setDeleteError(null);
      await deleteQuotation(targetId);
      queryClient.invalidateQueries({ queryKey: ['quotation'] });
      queryClient.invalidateQueries({ queryKey: ['quotations'] });
      await refreshQuotations();
      setIsDeleteModalOpen(false);
      navigate(ROUTES.QUOTATIONS);
    } catch (err: any) {
      console.error('Delete quotation failed:', err);
      setDeleteError(err?.response?.data?.detail || err?.message || 'Failed to delete quotation');
    } finally {
      setIsDeleting(false);
    }
  };

  // Layout View mode: 'balanced' (50/50), 'docFocus' (65/35), 'dataFocus' (35/65)
  const [layoutMode, setLayoutMode] = useState<'balanced' | 'docFocus' | 'dataFocus'>('balanced');
  const [mobileTab, setMobileTab] = useState<'document' | 'data'>('data');

  // Initialize editable state buffer from extraction data
  useEffect(() => {
    if (extraction) {
      const extData = extraction.extracted_data || {};
      setSupplier(
        extData.supplier || {
          supplier_name: extraction.supplier_name,
          quotation_number: extraction.quotation_number,
          contact_person: extraction.contact_person,
          email: extraction.contact_email,
          phone: extraction.contact_phone,
          address: extraction.supplier_address,
        }
      );

      setQuotationData(
        extData.quotation || {
          quotation_date: extraction.quotation_date || undefined,
          validity_date: extraction.validity_date || undefined,
          currency: extraction.currency || 'USD',
          subtotal: extraction.stated_subtotal !== null ? Number(extraction.stated_subtotal) : undefined,
          tax: extraction.stated_tax !== null ? Number(extraction.stated_tax) : undefined,
          discount: extraction.stated_discount !== null ? Number(extraction.stated_discount) : undefined,
          shipping: extraction.stated_shipping !== null ? Number(extraction.stated_shipping) : undefined,
          grand_total: extraction.stated_grand_total !== null ? Number(extraction.stated_grand_total) : undefined,
        }
      );

      setCommercialTerms(
        extData.commercial_terms || {
          delivery_time: extraction.delivery_time,
          delivery_terms: extraction.delivery_terms,
          payment_terms: extraction.payment_terms,
          warranty: extraction.warranty,
          notes: extraction.notes,
        }
      );

      setLineItems(extData.line_items || []);
      setHasUnsavedChanges(false);
    }
  }, [extraction]);

  // Handle updates to Supplier fields
  const handleSupplierChange = (field: keyof ExtractedSupplierData, value: string) => {
    setSupplier((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Handle updates to Quotation metadata
  const handleQuotationChange = (field: keyof ExtractedQuotationData, value: any) => {
    setQuotationData((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Handle updates to Commercial Terms
  const handleCommercialTermsChange = (field: keyof ExtractedCommercialTermsData, value: string) => {
    setCommercialTerms((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
  };

  // Handle updates to Line Items
  const handleLineItemsChange = (updatedItems: ExtractedLineItemData[]) => {
    setLineItems(updatedItems);
    setHasUnsavedChanges(true);
  };

  // Coordinate clicking an Evidence Badge with Document Viewer
  const handleEvidenceClick = (fieldName: string, evidence: FieldEvidence) => {
    setSelectedEvidenceSnippet({
      page: evidence.page_number,
      text: evidence.source_text,
      fieldName,
    });
  };

  // Save human corrections to backend
  const handleSaveCorrections = async () => {
    if (!extraction) return;

    try {
      await saveCorrectionsMutation.mutateAsync({
        id: extraction.id,
        payload: {
          supplier,
          quotation: quotationData,
          commercial_terms: commercialTerms,
          line_items: lineItems,
          reason: 'Human review corrections saved via Review Console',
        },
      });

      setHasUnsavedChanges(false);
      setSaveSuccessMessage('Corrections saved and deterministic validation recomputed successfully.');
      setTimeout(() => setSaveSuccessMessage(null), 4000);
    } catch (err: any) {
      console.error('Failed to save corrections:', err);
    }
  };

  // Approve extraction and apply to official quotation atomically
  const handleApproveConfirm = async (payload: { review_notes?: string; apply_to_quotation?: boolean }) => {
    if (!extraction) return;

    try {
      setApproveError(null);
      await approveExtractionMutation.mutateAsync({
        id: extraction.id,
        payload,
      });

      setIsApproveModalOpen(false);
      setSaveSuccessMessage('Quotation approved successfully and verified status recorded.');
      setTimeout(() => setSaveSuccessMessage(null), 4000);
    } catch (err: unknown) {
      console.error('Failed to approve extraction:', err);
      const errorMsg = getErrorMessage(err, 'Failed to approve extraction. Please verify your permissions.');
      setApproveError(errorMsg);
    }
  };

  // Reject extraction
  const handleReject = async () => {
    if (!extraction) return;
    if (!canReject) {
      setActionErrorMessage('You do not have permission to reject quotation extractions.');
      setTimeout(() => setActionErrorMessage(null), 5000);
      return;
    }
    const reason = window.prompt('Please enter the reason for rejecting this extraction:');
    if (!reason || !reason.trim()) return;

    try {
      setActionErrorMessage(null);
      await rejectExtractionMutation.mutateAsync({
        id: extraction.id,
        reason: reason.trim(),
      });
      setSaveSuccessMessage('Extraction rejected and marked for reprocessing.');
      setTimeout(() => setSaveSuccessMessage(null), 4000);
    } catch (err: unknown) {
      console.error('Failed to reject extraction:', err);
      const errorMsg = getErrorMessage(err, 'Failed to reject extraction.');
      setActionErrorMessage(errorMsg);
      setTimeout(() => setActionErrorMessage(null), 6000);
    }
  };

  // Trigger retry if extraction failed
  const handleRetryExtraction = async () => {
    if (extraction?.document_id) {
      try {
        const res = await triggerExtractionMutation.mutateAsync({
          documentId: extraction.document_id,
          sync: true,
        });
        if (res && (res as any).id) {
          setLocalExtraction(res as BackendQuotationExtraction);
        }
      } catch (err) {
        console.error('Retry extraction failed:', err);
      }
    }
  };

  // Re-calculate local item totals for display
  const calculatedItemsSubtotal = useMemo(() => {
    return lineItems.reduce((acc, item) => acc + (Number(item.total) || 0), 0);
  }, [lineItems]);

  const calculatedGrandTotal = useMemo(() => {
    const tax = Number(quotationData.tax) || 0;
    const shipping = Number(quotationData.shipping) || 0;
    const discount = Number(quotationData.discount) || 0;
    return Math.round((calculatedItemsSubtotal + tax + shipping - discount) * 100) / 100;
  }, [calculatedItemsSubtotal, quotationData]);

  // Loading State
  if (isLoading) {
    return (
      <PageContainer>
        <div className="py-24 flex flex-col items-center justify-center space-y-4 text-slate-500">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
          <div className="text-center">
            <h3 className="text-sm font-semibold text-slate-900">Loading AI Quotation Review...</h3>
            <p className="text-xs text-slate-500 mt-1">Retrieving extracted data and deterministic flags</p>
          </div>
        </div>
      </PageContainer>
    );
  }

  // Quotation deleted or not found
  if (quotationDetailQuery.isError && !quotation) {
    return (
      <PageContainer>
        <div className="text-center py-20 max-w-lg mx-auto space-y-4">
          <div className="w-16 h-16 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto text-rose-500">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Quotation Not Found</h2>
          <p className="text-xs text-slate-500 leading-relaxed">
            This quotation does not exist or has been deleted from your organization.
          </p>
          <div className="pt-2">
            <Link to={ROUTES.QUOTATIONS}>
              <Button variant="primary" size="sm">
                ← Return to Quotations List
              </Button>
            </Link>
          </div>
        </div>
      </PageContainer>
    );
  }

  // Not Found or Ready to Extract State
  if (!extraction) {
    const attachedDoc = quotation?.documents?.[0];
    return (
      <PageContainer>
        <div className="text-center py-20 max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-indigo-600" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">
            {attachedDoc ? 'Quotation Document Ready for AI Extraction' : 'Extraction Record Not Found'}
          </h2>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            {attachedDoc
              ? `Document "${attachedDoc.originalFilename}" is attached to this quotation. Run Gemini 2.0 to extract line items, prices, commercial terms, and deterministic validation flags.`
              : `No extraction matching "${id}" was found or you may not have access to this document.`}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link to={ROUTES.QUOTATIONS}>
              <Button variant="outline" size="sm">
                Back to Quotations
              </Button>
            </Link>
            {attachedDoc && (
              <div className="flex flex-col items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={triggerExtractionMutation.isPending}
                  onClick={async () => {
                    try {
                      const res = await triggerExtractionMutation.mutateAsync({
                        documentId: attachedDoc.id,
                        sync: true,
                      });
                      if (res && (res as any).id) {
                        setLocalExtraction(res as BackendQuotationExtraction);
                      }
                    } catch (err) {
                      console.error('Trigger extraction failed:', err);
                    }
                  }}
                  leftIcon={triggerExtractionMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                >
                  {triggerExtractionMutation.isPending ? 'Extracting with Gemini 2.0...' : 'Extract with Gemini 2.0'}
                </Button>
                {triggerExtractionMutation.isError && (
                  <p className="text-xs text-rose-500 font-medium">
                    {(triggerExtractionMutation.error as any)?.response?.data?.detail || triggerExtractionMutation.error.message || 'Extraction failed. Please check Gemini API key.'}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    );
  }

  // Processing or Pending State
  if (extraction.status === 'processing' || extraction.status === 'pending') {
    const docId = extraction.document_id || quotation?.documents?.[0]?.id;
    return (
      <PageContainer>
        <div className="max-w-2xl mx-auto py-16 space-y-6">
          <div className="p-8 bg-white border border-slate-200 rounded-2xl shadow-sm text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-900">
                Document Extraction in Progress...
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                Gemini 2.0 is reading <span className="font-semibold text-slate-800">{extraction.document_filename || quotation?.fileName || 'quotation document'}</span>,
                extracting supplier metadata, commercial terms, line item pricing, and running deterministic validation rules.
              </p>
            </div>

            <div className="w-full max-w-md mx-auto bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div className="bg-indigo-600 h-2.5 rounded-full animate-pulse w-3/4" />
            </div>

            <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400 font-mono">
              <Clock className="w-3.5 h-3.5" />
              <span>Status: {extraction.status.toUpperCase()} • Polling server every 2.5s</span>
            </div>

            {/* Escape Controls if process is taking too long or worker died */}
            <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-center gap-3">
              {docId && (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={triggerExtractionMutation.isPending}
                  onClick={async () => {
                    try {
                      const res = await triggerExtractionMutation.mutateAsync({
                        documentId: docId,
                        sync: true,
                      });
                      if (res && (res as any).id) {
                        setLocalExtraction(res as BackendQuotationExtraction);
                      }
                    } catch (err) {
                      console.error('Trigger extraction failed:', err);
                    }
                  }}
                  leftIcon={triggerExtractionMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                >
                  {triggerExtractionMutation.isPending ? 'Extracting...' : 'Force Re-Extract with Gemini'}
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={() => setLocalExtraction(null)}
                className="text-xs"
              >
                Reset View
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteModalOpen(true)}
                className="text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Delete Quotation
              </Button>
            </div>
            {triggerExtractionMutation.isError && (
              <p className="text-xs text-rose-500 font-medium">
                {(triggerExtractionMutation.error as any)?.response?.data?.detail || triggerExtractionMutation.error.message || 'Extraction failed.'}
              </p>
            )}
          </div>

          <div className="text-center">
            <Link to={ROUTES.QUOTATIONS} className="text-xs text-slate-500 hover:text-indigo-600">
              ← Return to Quotations List
            </Link>
          </div>
        </div>

        {/* Delete Quotation Modal */}
        {isDeleteModalOpen && (
          <DeleteQuotationModal
            isOpen={isDeleteModalOpen}
            onClose={() => {
              setIsDeleteModalOpen(false);
              setDeleteError(null);
            }}
            quotation={quotation || null}
            onConfirm={handleDeleteQuotation}
            isDeleting={isDeleting}
            error={deleteError}
          />
        )}
      </PageContainer>
    );
  }

  // Failed State
  if (extraction.status === 'failed') {
    return (
      <PageContainer>
        <div className="max-w-xl mx-auto py-16 space-y-4">
          <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-center space-y-3">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
            <h3 className="text-base font-bold text-rose-900">Quotation Extraction Failed</h3>
            <p className="text-xs text-rose-700 leading-relaxed">
              {extraction.error_message || 'An unexpected error occurred while parsing the document with Gemini.'}
            </p>
            <div className="pt-2 flex justify-center gap-3">
              <Link to={ROUTES.QUOTATIONS}>
                <Button variant="outline" size="sm">
                  Cancel
                </Button>
              </Link>
              <Button
                variant="primary"
                size="sm"
                onClick={handleRetryExtraction}
                disabled={triggerExtractionMutation.isPending}
                leftIcon={<RotateCw className={`w-3.5 h-3.5 ${triggerExtractionMutation.isPending ? 'animate-spin' : ''}`} />}
              >
                {triggerExtractionMutation.isPending ? 'Retrying...' : 'Retry Extraction'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteModalOpen(true)}
                className="text-rose-600 hover:bg-rose-50"
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Delete Quotation
              </Button>
            </div>
          </div>
        </div>

        {/* Delete Quotation Modal */}
        {isDeleteModalOpen && (
          <DeleteQuotationModal
            isOpen={isDeleteModalOpen}
            onClose={() => {
              setIsDeleteModalOpen(false);
              setDeleteError(null);
            }}
            quotation={quotation || null}
            onConfirm={handleDeleteQuotation}
            isDeleting={isDeleting}
            error={deleteError}
          />
        )}
      </PageContainer>
    );
  }

  const evidenceMap = extraction.extracted_data?.evidence || {};
  const isApproved = extraction.is_approved || extraction.review_status === 'approved';

  return (
    <PageContainer>
      <div className="space-y-4">
        {/* Top Header & Action Controls Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-slate-200">
          <div className="flex items-center space-x-3">
            <Link
              to={ROUTES.QUOTATIONS}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
              title="Back to Quotations"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>

            <div>
              <div className="flex items-center space-x-2 flex-wrap">
                <h1 className="text-lg font-bold text-slate-900">
                  {extraction.supplier_name || 'AI Extraction Review'}
                </h1>
                {extraction.quotation_number && (
                  <span className="font-mono text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                    Ref: {extraction.quotation_number}
                  </span>
                )}
                <span
                  className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                    isApproved
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}
                >
                  {isApproved ? 'Verified & Approved' : 'Pending Review'}
                </span>
                {hasUnsavedChanges && (
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500 text-white animate-pulse">
                    Unsaved Edits
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                <span>File: {extraction.document_filename}</span>
                <span>•</span>
                <span>Model: {extraction.model_name}</span>
                {extraction.processing_time_ms && (
                  <>
                    <span>•</span>
                    <span className="font-mono">{(extraction.processing_time_ms / 1000).toFixed(1)}s extraction</span>
                  </>
                )}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2 flex-wrap">
            {/* Layout switch controls (desktop) */}
            <div className="hidden md:flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 mr-2 text-xs">
              <button
                type="button"
                onClick={() => setLayoutMode('docFocus')}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  layoutMode === 'docFocus' ? 'bg-white shadow-2xs font-semibold text-slate-900' : 'text-slate-600'
                }`}
                title="65% Document / 35% Data"
              >
                Doc View
              </button>
              <button
                type="button"
                onClick={() => setLayoutMode('balanced')}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  layoutMode === 'balanced' ? 'bg-white shadow-2xs font-semibold text-slate-900' : 'text-slate-600'
                }`}
                title="50% Document / 50% Data"
              >
                Split
              </button>
              <button
                type="button"
                onClick={() => setLayoutMode('dataFocus')}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  layoutMode === 'dataFocus' ? 'bg-white shadow-2xs font-semibold text-slate-900' : 'text-slate-600'
                }`}
                title="35% Document / 65% Data"
              >
                Data View
              </button>
            </div>

            {/* Audit History Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAuditModalOpen(true)}
              leftIcon={<History className="w-3.5 h-3.5" />}
              className="text-xs"
            >
              Audit Trail ({extraction.corrections_count || 0})
            </Button>

            {/* Save Corrections Button */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSaveCorrections}
              disabled={saveCorrectionsMutation.isPending || !hasUnsavedChanges}
              leftIcon={
                saveCorrectionsMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Save className="w-3.5 h-3.5" />
                )
              }
              className="text-xs"
            >
              {saveCorrectionsMutation.isPending ? 'Saving...' : 'Save Corrections'}
            </Button>

            {/* Approve / Reject Buttons */}
            {!isApproved ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReject}
                  disabled={rejectExtractionMutation.isPending || !canReject}
                  title={!canReject ? 'You do not have permission to reject quotation extractions.' : undefined}
                  leftIcon={<XCircle className="w-3.5 h-3.5 text-rose-500" />}
                  className={`text-xs ${
                    canReject
                      ? 'text-rose-700 hover:bg-rose-50 border-rose-200'
                      : 'opacity-50 cursor-not-allowed text-slate-400 border-slate-200'
                  }`}
                >
                  Reject
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    if (!canApprove) return;
                    setApproveError(null);
                    setIsApproveModalOpen(true);
                  }}
                  disabled={approveExtractionMutation.isPending || !canApprove}
                  title={!canApprove ? 'Only procurement managers or administrators can approve quotation extractions.' : undefined}
                  leftIcon={<ShieldCheck className="w-3.5 h-3.5" />}
                  className={`text-xs ${
                    canApprove
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white focus:ring-emerald-500'
                      : 'opacity-50 cursor-not-allowed bg-slate-300 text-slate-500 hover:bg-slate-300'
                  }`}
                >
                  Approve Extraction
                </Button>
              </>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Verified by {extraction.approved_by_email || 'Procurement'}</span>
              </div>
            )}
          </div>
        </div>

        {/* Success Alert Banner */}
        {saveSuccessMessage && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800 animate-in fade-in">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-600" />
              <span>{saveSuccessMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setSaveSuccessMessage(null)}
              className="text-emerald-600 hover:text-emerald-800 font-bold"
            >
              ×
            </button>
          </div>
        )}

        {/* Warning Alert Banner (Issue 10) */}
        {saveWarningMessage && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs text-amber-800 animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>{saveWarningMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setSaveWarningMessage(null)}
              className="text-amber-600 hover:text-amber-800 font-bold"
            >
              ×
            </button>
          </div>
        )}

        {/* Action Error Alert Banner (Issue 9) */}
        {actionErrorMessage && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-xs text-rose-800 animate-in fade-in">
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{actionErrorMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setActionErrorMessage(null)}
              className="text-rose-600 hover:text-rose-800 font-bold"
            >
              ×
            </button>
          </div>
        )}

        {/* Confidence Score & Human Verification Notice */}
        <ConfidenceScoreMeter
          score={extraction.overall_confidence || 0.9}
          isApproved={isApproved}
        />

        {/* Mobile View Toggle */}
        <div className="md:hidden flex border-b border-slate-200">
          <button
            type="button"
            onClick={() => setMobileTab('data')}
            className={`flex-1 py-2 text-center text-xs font-semibold border-b-2 transition-colors ${
              mobileTab === 'data'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500'
            }`}
          >
            Extracted Data & Review
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('document')}
            className={`flex-1 py-2 text-center text-xs font-semibold border-b-2 transition-colors ${
              mobileTab === 'document'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500'
            }`}
          >
            Original Document Preview
          </button>
        </div>

        {/* Split Screen Workspace Container */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
          {/* Left Pane: Original Quotation Document Viewer */}
          <div
            className={`h-[800px] sticky top-4 ${
              mobileTab === 'document' ? 'block' : 'hidden md:block'
            } ${
              layoutMode === 'docFocus'
                ? 'md:col-span-7'
                : layoutMode === 'dataFocus'
                ? 'md:col-span-4'
                : 'md:col-span-6'
            }`}
          >
            <DocumentViewer
              documentId={extraction.document_id}
              fileName={extraction.document_filename}
              activePage={selectedEvidenceSnippet?.page}
              evidenceSnippet={selectedEvidenceSnippet}
              onClearSnippet={() => setSelectedEvidenceSnippet(null)}
            />
          </div>

          {/* Right Pane: Review Cards & Line Items Editor */}
          <div
            className={`space-y-5 ${
              mobileTab === 'data' ? 'block' : 'hidden md:block'
            } ${
              layoutMode === 'docFocus'
                ? 'md:col-span-5'
                : layoutMode === 'dataFocus'
                ? 'md:col-span-8'
                : 'md:col-span-6'
            }`}
          >
            {/* Deterministic Validation Flags Card */}
            <ValidationFlagsCard
              flags={extraction.validation_flags || []}
            />

            {/* Extracted Supplier Information Card */}
            <ExtractionSupplierInfoCard
              supplier={supplier}
              evidenceMap={evidenceMap}
              onChange={handleSupplierChange}
              onEvidenceClick={handleEvidenceClick}
              isReadOnly={isApproved}
            />

            {/* Extracted Quotation Metadata & Commercial Terms Card */}
            <ExtractionQuotationInfoCard
              quotation={quotationData}
              commercialTerms={commercialTerms}
              evidenceMap={evidenceMap}
              onQuotationChange={handleQuotationChange}
              onCommercialTermsChange={handleCommercialTermsChange}
              onEvidenceClick={handleEvidenceClick}
              isReadOnly={isApproved}
            />

            {/* Extracted Line Items Editor Table */}
            <ExtractionLineItemsEditor
              items={lineItems}
              currency={quotationData.currency || 'USD'}
              onChange={handleLineItemsChange}
              onEvidenceClick={handleEvidenceClick}
              isReadOnly={isApproved}
            />

            {/* Financial Reconciliation & Deterministic Math Card */}
            <ExtractionFinancialsCard
              statedSubtotal={quotationData.subtotal}
              statedTax={quotationData.tax}
              statedDiscount={quotationData.discount}
              statedShipping={quotationData.shipping}
              statedGrandTotal={quotationData.grand_total}
              calculatedItemsSubtotal={calculatedItemsSubtotal}
              calculatedGrandTotal={calculatedGrandTotal}
              isMathConsistent={extraction.is_math_consistent}
              totalVariance={extraction.total_variance}
              currency={quotationData.currency || 'USD'}
              onQuotationChange={handleQuotationChange}
              isReadOnly={isApproved}
            />

            {/* Sticky Bottom Actions Bar */}
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between gap-3 sticky bottom-4 z-20">
              <div className="text-xs text-slate-500">
                {hasUnsavedChanges ? (
                  <span className="text-amber-700 font-semibold flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                    You have unsaved corrections. Save before approving.
                  </span>
                ) : isApproved ? (
                  <span className="text-emerald-700 font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Extraction verified and locked.
                  </span>
                ) : (
                  <span>All current edits are up to date.</span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleSaveCorrections}
                  disabled={saveCorrectionsMutation.isPending || !hasUnsavedChanges}
                  leftIcon={<Save className="w-3.5 h-3.5" />}
                  className="text-xs"
                >
                  Save Corrections
                </Button>

                {!isApproved && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      if (!canApprove) return;
                      setApproveError(null);
                      setIsApproveModalOpen(true);
                    }}
                    disabled={approveExtractionMutation.isPending || !canApprove}
                    title={!canApprove ? 'Only procurement managers or administrators can approve quotation extractions.' : undefined}
                    leftIcon={<ShieldCheck className="w-3.5 h-3.5" />}
                    className={`text-xs ${
                      canApprove
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                        : 'opacity-50 cursor-not-allowed bg-slate-300 text-slate-500 hover:bg-slate-300'
                    }`}
                  >
                    Approve
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDeleteModalOpen(true)}
                  leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                  className="text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                >
                  Delete Quotation
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Quotation Modal */}
      {isDeleteModalOpen && (
        <DeleteQuotationModal
          isOpen={isDeleteModalOpen}
          onClose={() => {
            setIsDeleteModalOpen(false);
            setDeleteError(null);
          }}
          quotation={quotation || null}
          onConfirm={handleDeleteQuotation}
          isDeleting={isDeleting}
          error={deleteError}
        />
      )}

      {/* Approve Extraction Modal */}
      {isApproveModalOpen && (
        <ApproveExtractionModal
          isOpen={isApproveModalOpen}
          onClose={() => {
            setIsApproveModalOpen(false);
            setApproveError(null);
          }}
          extraction={extraction}
          existingItemCount={quotation?.extractedItems?.length}
          onConfirmApprove={handleApproveConfirm}
          isApproving={approveExtractionMutation.isPending}
          error={approveError}
        />
      )}

      {/* Audit History Modal */}
      {isAuditModalOpen && (
        <AuditHistoryModal
          isOpen={isAuditModalOpen}
          onClose={() => setIsAuditModalOpen(false)}
          extractionId={extraction.id}
        />
      )}
    </PageContainer>
  );
};
