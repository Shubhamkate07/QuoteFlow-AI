import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageLoading } from '../../components/feedback/PageLoading';
import { RfqStatusBadge } from '../../features/rfq/components/RfqStatusBadge';
import { DeleteRfqModal } from '../../features/rfq/components/DeleteRfqModal';
import { RfqItemsSection } from '../../features/rfq/components/RfqItemsSection';
import { QuotationManagementSection } from '../../features/quotations/components/QuotationManagementSection';
import { useRfqDetail, useDeleteRfq } from '../../features/rfq/hooks/useRfqQueries';
import { useQuotation } from '../../features/quotations/context/QuotationContext';
import { ROUTES } from '../../routes/paths';
import { formatDate } from '../../utils/formatters';
import { SupplierSelector } from '../../features/suppliers/components/SupplierSelector';
import {
  Edit,
  Trash2,
  Calendar,
  DollarSign,
  FileText,
  GitCompare,
  Package,
  Users,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export const RfqDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: rfq,
    isLoading,
    isError,
    error,
    refetch,
  } = useRfqDetail(id);

  const deleteRfqMutation = useDeleteRfq();
  const { getQuotationsByRfq } = useQuotation();

  const rfqQuotes = rfq ? getQuotationsByRfq(rfq.id) : [];

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [invitedSupplierIds, setInvitedSupplierIds] = useState<string[]>(['sup-1', 'sup-2']);

  if (isLoading) {
    return (
      <PageContainer>
        <PageLoading message="Loading RFQ specification and line items..." />
      </PageContainer>
    );
  }

  if (isError || !rfq) {
    return (
      <PageContainer>
        <div className="text-center py-16 max-w-md mx-auto space-y-4">
          <div className="inline-flex p-3 rounded-full bg-rose-50 text-rose-600 mb-1">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">RFQ Not Found</h2>
          <p className="text-sm text-slate-500">
            {(error as any)?.message ||
              `The requested RFQ record (${id}) does not exist in your organization or has been deleted.`}
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry
            </Button>
            <Link to={ROUTES.RFQS}>
              <Button variant="primary" size="sm">
                Back to RFQs List
              </Button>
            </Link>
          </div>
        </div>
      </PageContainer>
    );
  }

  const handleConfirmDelete = () => {
    deleteRfqMutation.mutate(rfq.id, {
      onSuccess: () => {
        navigate(ROUTES.RFQS);
      },
    });
  };

  return (
    <PageContainer>
      <PageHeader
        breadcrumbs={[
          { label: 'RFQs', href: ROUTES.RFQS },
          { label: rfq.rfqNumber },
        ]}
        title={rfq.title}
        description={`Requisition reference ${rfq.rfqNumber} • Created ${formatDate(rfq.createdAt)}`}
        actions={
          <div className="flex items-center gap-2">
            <Link to={ROUTES.RFQ_EDIT(rfq.id)}>
              <Button variant="outline" size="sm" leftIcon={<Edit className="w-4 h-4" />}>
                Edit RFQ
              </Button>
            </Link>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDeleteModalOpen(true)}
              className="text-rose-600 hover:bg-rose-50 hover:text-rose-700"
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              Delete
            </Button>

            <Link to={`${ROUTES.COMPARISON}?rfqId=${rfq.id}`}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<GitCompare className="w-4 h-4" />}
              >
                Compare Quotes ({rfqQuotes.length})
              </Button>
            </Link>
          </div>
        }
      />

      {/* Main Grid: Parameters & Invited Bidders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Left Column (2 Cols): Overview Parameters */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Requisition Overview</CardTitle>
                <RfqStatusBadge status={rfq.status} />
              </div>
              <CardDescription>Primary procurement scope and delivery specifications</CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {rfq.description && (
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                    Scope Description
                  </span>
                  <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-lg border border-slate-100">
                    {rfq.description}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>Required Delivery</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-900">
                    {rfq.requiredDeliveryDate ? formatDate(rfq.requiredDeliveryDate) : 'Open'}
                  </div>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                    <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                    <span>Currency Standard</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-900 font-mono">
                    {rfq.currency}
                  </div>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <div className="flex items-center space-x-2 text-slate-500 text-xs mb-1">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    <span>Last Updated</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-900">
                    {formatDate(rfq.updatedAt)}
                  </div>
                </div>
              </div>

              {rfq.notes && (
                <div className="pt-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                    Procurement Terms & Notes
                  </span>
                  <p className="text-xs text-slate-600 bg-slate-50/70 p-3 rounded-lg border border-slate-100 leading-relaxed font-mono">
                    {rfq.notes}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1 Col): Invited Suppliers Selector & Guidance */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4 text-slate-500" />
                  <CardTitle>Invited Bidders</CardTitle>
                </div>
                <Badge variant="neutral" size="sm">
                  {invitedSupplierIds.length} Invited
                </Badge>
              </div>
              <CardDescription>Select suppliers from directory to submit quotation bids</CardDescription>
            </CardHeader>
            <CardContent>
              <SupplierSelector
                selectedSupplierIds={invitedSupplierIds}
                onChange={setInvitedSupplierIds}
                label="Active RFQ Supplier Invitations"
                helperText="Suppliers invited here appear in the quotation upload dialog."
              />
            </CardContent>
          </Card>

          {/* Guidance Card */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs text-slate-600 shadow-2xs">
            <div className="flex items-center space-x-2 font-semibold text-slate-900">
              <Package className="w-4 h-4 text-indigo-600" />
              <span>QuoteFlow Extraction Engine</span>
            </div>
            <p className="leading-relaxed text-slate-500">
              Upload vendor quotations in PDF, Excel, or scanned formats below. QuoteFlow extracts line-item pricing, detects alloy/spec differences, and validates delivery terms.
            </p>
          </div>
        </div>
      </div>

      {/* Interactive RFQ Requirements and Items Management Section */}
      <div className="mb-8">
        <RfqItemsSection
          rfqId={rfq.id}
          items={rfq.items}
          currency={rfq.currency}
          defaultDeliveryDate={rfq.requiredDeliveryDate}
        />
      </div>

      {/* Interactive Quotation Management Section */}
      <div className="mb-8">
        <QuotationManagementSection
          rfqId={rfq.id}
          rfqCurrency={rfq.currency}
          rfqItems={rfq.items}
          invitedSupplierIds={invitedSupplierIds}
        />
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteRfqModal
        isOpen={isDeleteModalOpen}
        rfq={rfq}
        isDeleting={deleteRfqMutation.isPending}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
      />
    </PageContainer>
  );
};
