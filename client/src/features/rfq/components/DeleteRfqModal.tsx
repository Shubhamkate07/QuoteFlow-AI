import React from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { AlertTriangle } from 'lucide-react';
import type { Rfq } from '../types';

interface DeleteRfqModalProps {
  isOpen: boolean;
  rfq: Rfq | null;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export const DeleteRfqModal: React.FC<DeleteRfqModalProps> = ({
  isOpen,
  rfq,
  onClose,
  onConfirm,
  isDeleting = false,
}) => {
  if (!rfq) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Request for Quotation"
      description="This action cannot be undone."
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
            Permanently Delete
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
            Are you sure you want to delete <span className="font-semibold text-slate-900">{rfq.rfqNumber} — {rfq.title}</span>?
          </p>
          <p className="text-slate-500">
            All defined requirements, line item specifications, and associated quotation records will be permanently removed from this workspace.
          </p>
        </div>
      </div>
    </Modal>
  );
};
