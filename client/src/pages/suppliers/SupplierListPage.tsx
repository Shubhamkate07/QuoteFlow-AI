import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../components/ui/Table';
import { EmptyState } from '../../components/feedback/EmptyState';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { SupplierFilterBar } from '../../features/suppliers/components/SupplierFilterBar';
import { DeleteSupplierModal } from '../../features/suppliers/components/DeleteSupplierModal';
import { useSuppliers, useDeleteSupplier } from '../../features/suppliers/hooks/useSupplierQueries';
import type { Supplier } from '../../features/suppliers/types';
import { ROUTES } from '../../routes/paths';
import {
  Plus,
  Eye,
  Edit,
  Trash2,
  Building2,
  Mail,
  Phone,
  Star,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export const SupplierListPage: React.FC = () => {
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [countryFilter, setCountryFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [supplierToDelete, setSupplierToDelete] = useState<Supplier | null>(null);

  // TanStack Query: Fetch paginated & filtered suppliers from Django backend
  const {
    data,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useSuppliers({
    search: searchQuery,
    category: categoryFilter,
    status: statusFilter,
    country: countryFilter,
    page: currentPage,
  });

  const deleteSupplierMutation = useDeleteSupplier();

  const suppliers = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const handleResetFilters = () => {
    setSearchQuery('');
    setCategoryFilter('all');
    setStatusFilter('all');
    setCountryFilter('all');
    setCurrentPage(1);
  };

  const handleConfirmDelete = () => {
    if (supplierToDelete) {
      deleteSupplierMutation.mutate(supplierToDelete.id, {
        onSuccess: () => {
          setSupplierToDelete(null);
          if (suppliers.length === 1 && currentPage > 1) {
            setCurrentPage((p) => p - 1);
          }
        },
      });
    }
  };

  const categoryLabels: Record<string, string> = {
    machining: 'CNC Machining',
    fasteners: 'Fasteners & Hardware',
    sheet_metal: 'Sheet Metal',
    plastics: 'Polymers & Plastics',
    electronics: 'Electronics',
    surface_treatment: 'Surface Treatment',
    raw_materials: 'Raw Stock',
    other: 'Other Services',
  };

  const hasActiveFilters =
    Boolean(searchQuery) ||
    categoryFilter !== 'all' ||
    statusFilter !== 'all' ||
    countryFilter !== 'all';

  return (
    <PageContainer>
      <PageHeader
        title="Supplier Directory"
        description="Maintain approved vendor registries, manufacturing capabilities, quality ratings, and contact info."
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate(ROUTES.SUPPLIER_CREATE)}
          >
            Add Supplier
          </Button>
        }
      />

      {/* Filter Bar */}
      <SupplierFilterBar
        searchQuery={searchQuery}
        onSearchChange={(q) => {
          setSearchQuery(q);
          setCurrentPage(1);
        }}
        categoryFilter={categoryFilter}
        onCategoryChange={(c) => {
          setCategoryFilter(c);
          setCurrentPage(1);
        }}
        statusFilter={statusFilter}
        onStatusChange={(s) => {
          setStatusFilter(s);
          setCurrentPage(1);
        }}
        countryFilter={countryFilter}
        onCountryChange={(co) => {
          setCountryFilter(co);
          setCurrentPage(1);
        }}
        onReset={handleResetFilters}
      />

      {/* Supplier List */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <LoadingSpinner size="lg" label="Loading suppliers from server..." />
            </div>
          ) : isError ? (
            <div className="p-8 text-center space-y-3">
              <div className="inline-flex p-3 rounded-full bg-rose-50 text-rose-600 mb-1">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-slate-900">
                Failed to load suppliers
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                {(error as any)?.message || 'An error occurred while connecting to the Supplier directory.'}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Retry
              </Button>
            </div>
          ) : suppliers.length === 0 ? (
            <EmptyState
              icon={Building2}
              title={hasActiveFilters ? 'No suppliers match your search' : 'No suppliers registered yet'}
              description={
                hasActiveFilters
                  ? 'Adjust your search keywords or category filters, or clear them.'
                  : 'Add your approved vendors, machine shops, and component distributors to start inviting bids.'
              }
              actionLabel={hasActiveFilters ? 'Clear Filters' : 'Add First Supplier'}
              onAction={hasActiveFilters ? handleResetFilters : () => navigate(ROUTES.SUPPLIER_CREATE)}
              className="m-6"
            />
          ) : (
            <>
              {isFetching && !isLoading && (
                <div className="h-0.5 bg-indigo-500 animate-pulse w-full" />
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Company & Specialty</TableHead>
                    <TableHead>Contact Person</TableHead>
                    <TableHead>Communication</TableHead>
                    <TableHead>Country / Location</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suppliers.map((sup) => (
                    <TableRow key={sup.id}>
                      <TableCell>
                        <Link
                          to={ROUTES.SUPPLIER_DETAIL(sup.id)}
                          className="font-semibold text-slate-900 hover:text-indigo-600 transition-colors block text-sm"
                        >
                          {sup.companyName}
                        </Link>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="neutral" size="sm" className="text-[10px]">
                            {categoryLabels[sup.category] || sup.categoryDisplay || sup.category}
                          </Badge>
                          {sup.rating && (
                            <span className="text-[11px] font-semibold text-amber-600 flex items-center gap-0.5">
                              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                              {sup.rating.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </TableCell>

                      <TableCell className="text-xs font-medium text-slate-800">
                        {sup.contactPerson}
                      </TableCell>

                      <TableCell>
                        <div className="space-y-0.5 text-xs text-slate-600">
                          <div className="flex items-center space-x-1.5">
                            <Mail className="w-3 h-3 text-slate-400" />
                            <span className="truncate max-w-[180px]">{sup.email}</span>
                          </div>
                          {sup.phone && (
                            <div className="flex items-center space-x-1.5">
                              <Phone className="w-3 h-3 text-slate-400" />
                              <span>{sup.phone}</span>
                            </div>
                          )}
                        </div>
                      </TableCell>

                      <TableCell className="text-xs text-slate-600">
                        <span className="font-semibold text-slate-900 block">{sup.country}</span>
                        {sup.address && (
                          <span className="text-slate-400 max-w-[180px] truncate block text-[11px]">
                            {sup.address}
                          </span>
                        )}
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant={
                            sup.status === 'active'
                              ? 'success'
                              : sup.status === 'pending'
                              ? 'warning'
                              : 'neutral'
                          }
                          dot
                          size="sm"
                        >
                          {sup.statusDisplay || sup.status.toUpperCase()}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          <Link to={ROUTES.SUPPLIER_DETAIL(sup.id)}>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-1.5 h-8 w-8 text-slate-500 hover:text-slate-900"
                              title="View Supplier Details"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </Link>

                          <Link to={ROUTES.SUPPLIER_EDIT(sup.id)}>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-1.5 h-8 w-8 text-slate-500 hover:text-slate-900"
                              title="Edit Supplier"
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                          </Link>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSupplierToDelete(sup)}
                            className="p-1.5 h-8 w-8 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                            title="Delete Supplier"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}

          {/* Pagination Controls */}
          {totalCount > 0 && (
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
              <div>
                Showing{' '}
                <span className="font-semibold text-slate-800">
                  {(currentPage - 1) * pageSize + 1}
                </span>{' '}
                to{' '}
                <span className="font-semibold text-slate-800">
                  {Math.min(currentPage * pageSize, totalCount)}
                </span>{' '}
                of <span className="font-semibold text-slate-800">{totalCount}</span> Suppliers
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1 || isFetching}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="h-8 px-2.5 gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </Button>

                <span className="px-2 font-medium text-slate-700">
                  Page {currentPage} of {totalPages}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= totalPages || isFetching}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="h-8 px-2.5 gap-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <DeleteSupplierModal
        isOpen={Boolean(supplierToDelete)}
        supplier={supplierToDelete}
        isDeleting={deleteSupplierMutation.isPending}
        onClose={() => setSupplierToDelete(null)}
        onConfirm={handleConfirmDelete}
      />
    </PageContainer>
  );
};
