import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { PageLoading } from '../../components/feedback/PageLoading';
import { RfqForm } from '../../features/rfq/components/RfqForm';
import { useRfqDetail, useUpdateRfq } from '../../features/rfq/hooks/useRfqQueries';
import type { RfqFormValues } from '../../features/rfq/schemas/rfqSchema';
import { ROUTES } from '../../routes/paths';
import { AlertCircle, RefreshCw } from 'lucide-react';

export const EditRfqPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: rfq,
    isLoading,
    isError,
    error,
    refetch,
  } = useRfqDetail(id);

  const updateRfqMutation = useUpdateRfq();
  const [serverError, setServerError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <PageContainer>
        <PageLoading message="Loading RFQ parameters..." />
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
            {(error as any)?.message || `Cannot edit non-existent RFQ reference (${id}).`}
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

  const initialValues: Partial<RfqFormValues> = {
    title: rfq.title,
    rfqNumber: rfq.rfqNumber,
    description: rfq.description,
    requiredDeliveryDate: rfq.requiredDeliveryDate,
    currency: rfq.currency as any,
    status: rfq.status,
    notes: rfq.notes,
  };

  const handleSubmit = async (values: RfqFormValues) => {
    setServerError(null);
    try {
      await updateRfqMutation.mutateAsync({ id: rfq.id, values });
      navigate(ROUTES.RFQ_DETAIL(rfq.id));
    } catch (err: any) {
      const msg =
        err?.message ||
        err?.errors?.rfq_number?.[0] ||
        err?.errors?.title?.[0] ||
        'Failed to update RFQ parameters.';
      setServerError(msg);
    }
  };

  return (
    <PageContainer>
      <PageHeader
        breadcrumbs={[
          { label: 'RFQs', href: ROUTES.RFQS },
          { label: rfq.rfqNumber, href: ROUTES.RFQ_DETAIL(rfq.id) },
          { label: 'Edit' },
        ]}
        title={`Edit ${rfq.rfqNumber}`}
        description={`Modify requirements or lifecycle parameters for "${rfq.title}"`}
      />

      {serverError && (
        <div className="max-w-3xl mx-auto mb-5 p-3.5 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2.5 shadow-2xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span className="flex-1 font-medium">{serverError}</span>
          <button
            type="button"
            onClick={() => setServerError(null)}
            className="text-rose-400 hover:text-rose-700 text-sm font-semibold p-1"
          >
            ✕
          </button>
        </div>
      )}

      <RfqForm
        mode="edit"
        initialValues={initialValues}
        onSubmit={handleSubmit}
        onCancel={() => navigate(ROUTES.RFQ_DETAIL(rfq.id))}
        isSubmitting={updateRfqMutation.isPending}
      />
    </PageContainer>
  );
};
