import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { PageLoading } from '../../components/feedback/PageLoading';
import { SupplierForm } from '../../features/suppliers/components/SupplierForm';
import { useSupplierDetail, useUpdateSupplier } from '../../features/suppliers/hooks/useSupplierQueries';
import type { SupplierFormValues } from '../../features/suppliers/schemas/supplierSchema';
import { ROUTES } from '../../routes/paths';

export const EditSupplierPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: supplier, isLoading, isError } = useSupplierDetail(id);
  const updateSupplierMutation = useUpdateSupplier();
  const [serverError, setServerError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <PageContainer>
        <PageLoading message="Loading supplier details for editing..." />
      </PageContainer>
    );
  }

  if (isError || !supplier) {
    return (
      <PageContainer>
        <div className="text-center py-16">
          <h2 className="text-xl font-bold text-slate-900">Supplier Not Found</h2>
          <p className="text-sm text-slate-500 mt-1">
            Cannot edit supplier profile ({id}). It may have been deleted or belong to another organization.
          </p>
          <Link to={ROUTES.SUPPLIERS} className="mt-4 inline-block">
            <Button variant="outline" size="sm">
              Back to Supplier Directory
            </Button>
          </Link>
        </div>
      </PageContainer>
    );
  }

  const initialValues: Partial<SupplierFormValues> = {
    companyName: supplier.companyName,
    contactPerson: supplier.contactPerson,
    email: supplier.email,
    phone: supplier.phone,
    address: supplier.address,
    country: supplier.country || 'US',
    gstVatNumber: supplier.gstVatNumber,
    website: supplier.website,
    category: supplier.category,
    notes: supplier.notes,
    status: supplier.status,
  };

  const handleSubmit = async (values: SupplierFormValues) => {
    setServerError(null);
    try {
      await updateSupplierMutation.mutateAsync({
        id: supplier.id,
        values,
      });
      navigate(ROUTES.SUPPLIER_DETAIL(supplier.id));
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: Record<string, unknown> } };
      const data = apiErr.response?.data;
      let message = 'Failed to update supplier. Please check your inputs and try again.';
      if (data) {
        if (Array.isArray(data.company_name) && data.company_name[0]) {
          message = String(data.company_name[0]);
        } else if (Array.isArray(data.email) && data.email[0]) {
          message = String(data.email[0]);
        } else if (typeof data.detail === 'string') {
          message = data.detail;
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
          { label: supplier.companyName, href: ROUTES.SUPPLIER_DETAIL(supplier.id) },
          { label: 'Edit' },
        ]}
        title={`Edit ${supplier.companyName}`}
        description="Update vendor contact information, category accreditation, or status."
      />

      {serverError && (
        <div className="max-w-3xl mx-auto mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-red-900">Update Error</h4>
            <p className="text-sm text-red-700 mt-0.5">{serverError}</p>
          </div>
        </div>
      )}

      <SupplierForm
        key={supplier.id}
        mode="edit"
        initialValues={initialValues}
        onSubmit={handleSubmit}
        onCancel={() => navigate(ROUTES.SUPPLIER_DETAIL(supplier.id))}
        isSubmitting={updateSupplierMutation.isPending}
      />
    </PageContainer>
  );
};
