import React from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import type { Quotation } from '../types';
import { Trash2, AlertTriangle } from 'lucide-react';
import { formatCurrency } from '../../../utils/formatters';

interface DeleteQuotationModalProps {
  isOpen: boolean;
  onClose: () => void;
  quotation: Quotation | null;
  onConfirm: () => void;
  isDeleting?: boolean;
  error?: string | null;
}

export const DeleteQuotationModal: React.FC<DeleteQuotationModalProps> = ({
  isOpen,
  onClose,
  quotation,
  onConfirm,
  isDeleting = false,
  error = null,
}) => {
  if (!quotation) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Quotation"
      description="This action will permanently delete this quotation and its attached document files."
      maxWidth="md"
      footer={
        <div className="flex items-center justify-end gap-3 w-full">
          <Button variant="outline" type="button" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="button"
            onClick={onConfirm}
            isLoading={isDeleting}
            disabled={isDeleting}
            className="bg-rose-600 hover:bg-rose-700 focus:ring-rose-500 text-white"
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            {isDeleting ? 'Deleting...' : 'Delete Quotation'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-100 border border-rose-300 rounded-lg text-xs text-rose-900 font-medium">
            Deletion failed: {error}
          </div>
        )}

        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-xs text-rose-800">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
          <p>
            Are you sure you want to remove the quotation from{' '}
            <strong className="font-semibold">{quotation.supplierName}</strong>? The database record, line items, and all uploaded physical documents in storage will be removed.
          </p>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1.5 font-mono">
          <div className="flex justify-between">
            <span className="text-slate-500">Supplier:</span>
            <span className="font-semibold text-slate-900">{quotation.supplierName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Quote Ref:</span>
            <span className="font-semibold text-slate-900">{quotation.quoteReference}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">File Name:</span>
            <span className="text-slate-700 truncate max-w-[200px]">{quotation.fileName}</span>
          </div>
          {quotation.totalAmount > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">Total Value:</span>
              <span className="font-semibold text-emerald-700">
                {formatCurrency(quotation.totalAmount, quotation.currency)}
              </span>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
