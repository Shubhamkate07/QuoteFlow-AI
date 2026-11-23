import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
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
import { RfqFilterBar } from '../../features/rfq/components/RfqFilterBar';
import { RfqStatusBadge } from '../../features/rfq/components/RfqStatusBadge';
import { DeleteRfqModal } from '../../features/rfq/components/DeleteRfqModal';
import { useRfqs, useDeleteRfq } from '../../features/rfq/hooks/useRfqQueries';
import type { Rfq } from '../../features/rfq/types';
import { ROUTES } from '../../routes/paths';
import { formatDate } from '../../utils/formatters';
import {
  Plus,
  Eye,
  Edit,
  Trash2,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export const RfqListPage: React.FC = () => {
  const navigate = useNavigate();

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [currencyFilter, setCurrencyFilter] = useState('all');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Deletion Modal State
  const [rfqToDelete, setRfqToDelete] = useState<Rfq | null>(null);

  // TanStack Query: Fetch paginated & filtered RFQs from Django backend
  const {
    data,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useRfqs({
    search: searchQuery,
    status: statusFilter,
    currency: currencyFilter,
    page: currentPage,
  });

  const deleteRfqMutation = useDeleteRfq();

  const rfqs = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const handleResetFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
    setDateFilter('all');
    setCurrencyFilter('all');
    setCurrentPage(1);
  };

  const handleConfirmDelete = () => {
    if (rfqToDelete) {
      deleteRfqMutation.mutate(rfqToDelete.id, {
        onSuccess: () => {
          setRfqToDelete(null);
          // If deleted last item on current page, go to previous page
          if (rfqs.length === 1 && currentPage > 1) {
            setCurrentPage((p) => p - 1);
          }
        },
      });
    }
  };

  const hasActiveFilters =
    Boolean(searchQuery) ||
    statusFilter !== 'all' ||
    dateFilter !== 'all' ||
    currencyFilter !== 'all';

  return (
    <PageContainer>
      <PageHeader
        title="RFQ Management"
        description="Create and track Requests for Quotation, define item specifications, and monitor supplier bidding."
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate(ROUTES.RFQ_CREATE)}
          >
            Create RFQ
          </Button>
        }
      />

      {/* Filter Bar */}
      <RfqFilterBar
        searchQuery={searchQuery}
        onSearchChange={(q) => {
          setSearchQuery(q);
          setCurrentPage(1);
        }}
        statusFilter={statusFilter}
        onStatusChange={(s) => {
          setStatusFilter(s);
          setCurrentPage(1);
        }}
        dateFilter={dateFilter}
        onDateChange={(d) => {
          setDateFilter(d);
          setCurrentPage(1);
        }}
        currencyFilter={currencyFilter}
        onCurrencyChange={(c) => {
          setCurrencyFilter(c);
          setCurrentPage(1);
        }}
        onReset={handleResetFilters}
      />

      {/* RFQ List Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <LoadingSpinner size="lg" label="Loading RFQs from server..." />
            </div>
          ) : isError ? (
            <div className="p-8 text-center space-y-3">
              <div className="inline-flex p-3 rounded-full bg-rose-50 text-rose-600 mb-1">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-slate-900">
                Failed to load RFQs
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                {(error as any)?.message || 'An error occurred while connecting to the RFQ service.'}
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
          ) : rfqs.length === 0 ? (
            <EmptyState
              icon={FileSpreadsheet}
              title={hasActiveFilters ? 'No RFQs match your filters' : 'No RFQs created yet'}
              description={
                hasActiveFilters
                  ? 'Try adjusting your search query, status, or currency filters, or reset them.'
                  : 'Establish requirement baselines and invite supplier quotes by creating your first RFQ.'
              }
              actionLabel={hasActiveFilters ? 'Clear Filters' : 'Create First RFQ'}
              onAction={hasActiveFilters ? handleResetFilters : () => navigate(ROUTES.RFQ_CREATE)}
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
                    <TableHead>RFQ Reference</TableHead>
                    <TableHead>Title & Description</TableHead>
                    <TableHead>Required Delivery</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Items</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rfqs.map((rfq) => (
                    <TableRow key={rfq.id}>
                      <TableCell className="font-mono text-xs font-semibold text-slate-900">
                        <Link
                          to={ROUTES.RFQ_DETAIL(rfq.id)}
                          className="hover:text-indigo-600 transition-colors"
                        >
                          {rfq.rfqNumber}
                        </Link>
                      </TableCell>

                      <TableCell>
                        <Link
                          to={ROUTES.RFQ_DETAIL(rfq.id)}
                          className="font-medium text-slate-900 hover:text-indigo-600 transition-colors block text-sm"
                        >
                          {rfq.title}
                        </Link>
                        {rfq.description && (
                          <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                            {rfq.description}
                          </p>
                        )}
                      </TableCell>

                      <TableCell className="text-xs text-slate-600 font-medium whitespace-nowrap">
                        {rfq.requiredDeliveryDate ? formatDate(rfq.requiredDeliveryDate) : 'Not specified'}
                      </TableCell>

                      <TableCell>
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                          {rfq.currency}
                        </span>
                      </TableCell>

                      <TableCell>
                        <RfqStatusBadge status={rfq.status} size="sm" />
                      </TableCell>

                      <TableCell className="text-xs text-slate-700 font-semibold">
                        {rfq.itemsCount ?? rfq.items.length} {((rfq.itemsCount ?? rfq.items.length) === 1 ? 'item' : 'items')}
                      </TableCell>

                      <TableCell className="text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          <Link to={ROUTES.RFQ_DETAIL(rfq.id)}>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-1.5 h-8 w-8 text-slate-500 hover:text-slate-900"
                              title="View RFQ"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </Link>

                          <Link to={ROUTES.RFQ_EDIT(rfq.id)}>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-1.5 h-8 w-8 text-slate-500 hover:text-slate-900"
                              title="Edit RFQ"
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                          </Link>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setRfqToDelete(rfq)}
                            className="p-1.5 h-8 w-8 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                            title="Delete RFQ"
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
                of <span className="font-semibold text-slate-800">{totalCount}</span> RFQs
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
      <DeleteRfqModal
        isOpen={Boolean(rfqToDelete)}
        rfq={rfqToDelete}
        isDeleting={deleteRfqMutation.isPending}
        onClose={() => setRfqToDelete(null)}
        onConfirm={handleConfirmDelete}
      />
    </PageContainer>
  );
};
