import React from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { AlertTriangle } from 'lucide-react';
import type { RfqItem } from '../types';

interface DeleteItemModalProps {
  isOpen: boolean;
  item: RfqItem | null;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export const DeleteItemModal: React.FC<DeleteItemModalProps> = ({
  isOpen,
  item,
  onClose,
  onConfirm,
  isDeleting = false,
}) => {
  if (!item) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Required Item"
      description="Remove this line item requirement from the RFQ."
      maxWidth="md"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button variant="danger" size="sm" onClick={onConfirm} isLoading={isDeleting}>
            Remove Item
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
            Are you sure you want to delete{' '}
            <span className="font-semibold text-slate-900">
              {item.itemNumber}: {item.name}
            </span>
            ?
          </p>
          <p className="text-slate-500">
            Removing this item will exclude it from future quotation extraction comparisons.
          </p>
        </div>
      </div>
    </Modal>
  );
};
