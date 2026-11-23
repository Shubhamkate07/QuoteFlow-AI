import React from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { AlertTriangle } from 'lucide-react';
import type { Supplier } from '../types';

interface DeleteSupplierModalProps {
  isOpen: boolean;
  supplier: Supplier | null;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export const DeleteSupplierModal: React.FC<DeleteSupplierModalProps> = ({
  isOpen,
  supplier,
  onClose,
  onConfirm,
  isDeleting = false,
}) => {
  if (!supplier) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Supplier Profile"
      description="Remove this vendor from your approved procurement directory."
      maxWidth="md"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={onConfirm}
            isLoading={isDeleting}
          >
            Delete Supplier
          </Button>
        </>
      }
    >
      <div className="flex items-start space-x-3 text-slate-700">
        <div className="p-2 bg-rose-50 border border-rose-200 text-rose-600 rounded-lg shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="text-xs space-y-2 leading-relaxed">
          <p>
            Are you sure you want to remove{' '}
            <span className="font-semibold text-slate-900">{supplier.companyName}</span> from
            your supplier registry?
          </p>
          <p className="text-slate-500">
            Historical quotations uploaded from this supplier will retain their records, but this
            vendor will no longer appear in future RFQ invitation lists.
          </p>
        </div>
      </div>
    </Modal>
  );
};
