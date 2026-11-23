import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { SupplierForm } from '../../features/suppliers/components/SupplierForm';
import { useCreateSupplier } from '../../features/suppliers/hooks/useSupplierQueries';
import type { SupplierFormValues } from '../../features/suppliers/schemas/supplierSchema';
import { ROUTES } from '../../routes/paths';

export const CreateSupplierPage: React.FC = () => {
  const navigate = useNavigate();
  const createSupplierMutation = useCreateSupplier();
  const [serverError, setServerError] = useState<string | null>(null);

  const handleSubmit = async (values: SupplierFormValues) => {
    setServerError(null);
    try {
      const created = await createSupplierMutation.mutateAsync(values);
      navigate(ROUTES.SUPPLIER_DETAIL(created.id));
    } catch (err: unknown) {
      const apiErr = err as any;
      let message = apiErr?.message || 'Failed to create supplier. Please check the details and try again.';
      const data = apiErr?.response?.data || apiErr?.errors;
      if (data) {
        if (typeof data === 'string') {
          message = data;
        } else if (data.detail) {
          message = data.detail;
        } else if (data.message) {
          message = data.message;
        } else {
          const firstKey = Object.keys(data)[0];
          if (firstKey) {
            const val = data[firstKey];
            message = `${firstKey}: ${Array.isArray(val) ? val[0] : String(val)}`;
          }
        }
      }
      setServerError(message);
    }
  };

  return (
    <PageContainer>
      <PageHeader
        breadcrumbs={[
          { label: 'Suppliers', href: ROUTES.SUPPLIERS },
          { label: 'Add Supplier' },
        ]}
        title="Add Approved Supplier"
        description="Register an accredited vendor with contact coordinates and tax identifiers."
      />

      {serverError && (
        <div className="max-w-3xl mx-auto mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-red-900">Creation Error</h4>
            <p className="text-sm text-red-700 mt-0.5">{serverError}</p>
          </div>
        </div>
      )}

      <SupplierForm
        mode="create"
        onSubmit={handleSubmit}
        onCancel={() => navigate(ROUTES.SUPPLIERS)}
        isSubmitting={createSupplierMutation.isPending}
      />
    </PageContainer>
  );
};
