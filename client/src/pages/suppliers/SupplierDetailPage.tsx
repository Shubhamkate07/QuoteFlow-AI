import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageLoading } from '../../components/feedback/PageLoading';
import { DeleteSupplierModal } from '../../features/suppliers/components/DeleteSupplierModal';
import { useSupplierDetail, useDeleteSupplier } from '../../features/suppliers/hooks/useSupplierQueries';
import { ROUTES } from '../../routes/paths';
import {
  Edit,
  Trash2,
  Mail,
  Phone,
  MapPin,
  Globe,
  Hash,
  ShieldCheck,
  ExternalLink,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export const SupplierDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: supplier,
    isLoading,
    isError,
    error,
    refetch,
  } = useSupplierDetail(id);

  const deleteSupplierMutation = useDeleteSupplier();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  if (isLoading) {
    return (
      <PageContainer>
        <PageLoading message="Loading supplier profile..." />
      </PageContainer>
    );
  }

  if (isError || !supplier) {
    return (
      <PageContainer>
        <div className="text-center py-16 max-w-md mx-auto space-y-4">
          <div className="inline-flex p-3 rounded-full bg-rose-50 text-rose-600 mb-1">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">Supplier Not Found</h2>
          <p className="text-sm text-slate-500">
            {(error as any)?.message ||
              `The requested vendor record (${id}) does not exist in your organization or has been removed.`}
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
            <Link to={ROUTES.SUPPLIERS}>
              <Button variant="primary" size="sm">
                Back to Supplier Directory
              </Button>
            </Link>
          </div>
        </div>
      </PageContainer>
    );
  }

  const handleConfirmDelete = () => {
    deleteSupplierMutation.mutate(supplier.id, {
      onSuccess: () => {
        navigate(ROUTES.SUPPLIERS);
      },
    });
  };

  return (
    <PageContainer>
      <PageHeader
        breadcrumbs={[
          { label: 'Suppliers', href: ROUTES.SUPPLIERS },
          { label: supplier.companyName },
        ]}
        title={supplier.companyName}
        description={`Registered procurement vendor • Category: ${supplier.categoryDisplay || supplier.category.replace('_', ' ').toUpperCase()}`}
        actions={
          <div className="flex items-center gap-2">
            <Link to={ROUTES.SUPPLIER_EDIT(supplier.id)}>
              <Button variant="outline" size="sm" leftIcon={<Edit className="w-4 h-4" />}>
                Edit Profile
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
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Contact & Company Info */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Vendor Profile & Contact Details</CardTitle>
                <Badge
                  variant={supplier.status === 'active' ? 'success' : 'neutral'}
                  dot
                  size="sm"
                >
                  {supplier.statusDisplay || supplier.status.toUpperCase()}
                </Badge>
              </div>
              <CardDescription>Primary commercial communication and dispatch coordinates</CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-xs block mb-1">Primary Representative</span>
                  <div className="text-sm font-semibold text-slate-900">{supplier.contactPerson}</div>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-xs block mb-1">Business Email</span>
                  <a
                    href={`mailto:${supplier.email}`}
                    className="text-sm font-semibold text-indigo-600 hover:underline flex items-center gap-1.5"
                  >
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{supplier.email}</span>
                  </a>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-xs block mb-1">Direct Phone</span>
                  <div className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    <span>{supplier.phone || 'Not specified'}</span>
                  </div>
                </div>

                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-xs block mb-1">GST / VAT / Tax ID</span>
                  <div className="text-sm font-semibold text-slate-900 font-mono flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-slate-400" />
                    <span>{supplier.gstVatNumber || 'Not specified'}</span>
                  </div>
                </div>
              </div>

              {/* Physical Address & Country */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start space-x-2">
                <MapPin className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <span className="text-xs font-semibold text-slate-600 block">Dispatch & Billing Address</span>
                  <p className="text-xs text-slate-700 mt-0.5">{supplier.address || 'Address not provided'}</p>
                  <p className="text-xs text-slate-500 font-medium mt-1">Country: {supplier.country}</p>
                </div>
              </div>

              {/* Website Link */}
              {supplier.website && (
                <div className="pt-2">
                  <a
                    href={supplier.website.startsWith('http') ? supplier.website : `https://${supplier.website}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center text-xs text-indigo-600 hover:text-indigo-800 font-medium gap-1"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Visit Company Website</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notes and Certifications */}
          <Card>
            <CardHeader>
              <CardTitle>Technical Qualifications & Terms</CardTitle>
              <CardDescription>Manufacturing capabilities, inspection standards, and payment policies</CardDescription>
            </CardHeader>
            <CardContent>
              {supplier.notes ? (
                <p className="text-xs text-slate-700 bg-slate-50 p-4 rounded-lg border border-slate-200 leading-relaxed font-mono">
                  {supplier.notes}
                </p>
              ) : (
                <span className="text-xs text-slate-400 italic">No notes provided for this vendor.</span>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1 Col): Activity Summary */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Procurement History</CardTitle>
              <CardDescription>Bidding engagement and performance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <span className="text-xs text-slate-600 font-medium">Country of Origin</span>
                <span className="text-sm font-bold text-slate-900">{supplier.country}</span>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <span className="text-xs text-slate-600 font-medium">Quality & Delivery Rating</span>
                <span className="text-sm font-bold text-amber-600">
                  ★ {supplier.rating ? supplier.rating.toFixed(2) : '5.00'} / 5.00
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Action Card */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs text-slate-600 shadow-2xs">
            <div className="flex items-center space-x-2 font-semibold text-slate-900">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Verified Supplier</span>
            </div>
            <p className="leading-relaxed text-slate-500">
              This vendor is active in your workspace. You can invite them to ongoing RFQs and upload quotations received from them.
            </p>
          </div>
        </div>
      </div>

      <DeleteSupplierModal
        isOpen={isDeleteModalOpen}
        supplier={supplier}
        isDeleting={deleteSupplierMutation.isPending}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
      />
    </PageContainer>
  );
};
