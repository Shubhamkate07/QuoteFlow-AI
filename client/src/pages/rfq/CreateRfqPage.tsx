import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { RfqForm } from '../../features/rfq/components/RfqForm';
import { useCreateRfq } from '../../features/rfq/hooks/useRfqQueries';
import type { RfqFormValues } from '../../features/rfq/schemas/rfqSchema';
import { ROUTES } from '../../routes/paths';
import { AlertCircle } from 'lucide-react';

export const CreateRfqPage: React.FC = () => {
  const navigate = useNavigate();
  const createRfqMutation = useCreateRfq();
  const [serverError, setServerError] = useState<string | null>(null);

  const handleSubmit = async (values: RfqFormValues) => {
    setServerError(null);
    try {
      const created = await createRfqMutation.mutateAsync(values);
      navigate(ROUTES.RFQ_DETAIL(created.id));
    } catch (err: any) {
      let msg = err?.message || 'Failed to create RFQ. Please check the form parameters and try again.';
      const data = err?.response?.data || err?.errors;
      if (data) {
        if (typeof data === 'string') {
          msg = data;
        } else if (data.detail) {
          msg = data.detail;
        } else if (data.message) {
          msg = data.message;
        } else {
          const firstKey = Object.keys(data)[0];
          if (firstKey) {
            const val = data[firstKey];
            msg = `${firstKey}: ${Array.isArray(val) ? val[0] : String(val)}`;
          }
        }
      }
      setServerError(msg);
    }
  };

  return (
    <PageContainer>
      <PageHeader
        breadcrumbs={[
          { label: 'RFQs', href: ROUTES.RFQS },
          { label: 'Create RFQ' },
        ]}
        title="Create Request for Quotation"
        description="Establish requirement baseline, required delivery milestone, and currency rules."
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
        mode="create"
        onSubmit={handleSubmit}
        onCancel={() => navigate(ROUTES.RFQS)}
        isSubmitting={createRfqMutation.isPending}
      />
    </PageContainer>
  );
};
