import React, { useState } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import { Sparkles } from 'lucide-react';

interface CreateRfqModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => void;
}

export const CreateRfqModal: React.FC<CreateRfqModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('machining');
  const [deadline, setDeadline] = useState('2026-12-05');
  const [targetBaseline, setTargetBaseline] = useState('15000');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      onSubmit({
        title,
        category,
        deadline,
        targetBaseline: parseFloat(targetBaseline) || 0,
        notes,
      });
      setIsSubmitting(false);
      onClose();
    }, 600);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Request for Quotation"
      description="Define requirements and baseline targets before uploading vendor quotations."
      maxWidth="lg"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            leftIcon={<Sparkles className="w-3.5 h-3.5" />}
          >
            Create & Add Items
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Requisition / RFQ Title"
          placeholder="e.g. Precision CNC Aluminum 6061 Enclosures (Batch 3)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          helperText="A descriptive title recognized by suppliers and internal buyers."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="Procurement Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            options={[
              { value: 'machining', label: 'CNC Machining & Milling' },
              { value: 'sheet_metal', label: 'Sheet Metal Fabrication' },
              { value: 'fasteners', label: 'Hardware & Fasteners' },
              { value: 'plastics', label: 'Injection Molding & Polymers' },
              { value: 'electronics', label: 'PCBA & Cable Harnesses' },
              { value: 'raw_materials', label: 'Raw Bar & Plate Stock' },
            ]}
          />

          <Input
            label="Target Budget Baseline ($)"
            type="number"
            placeholder="15000"
            value={targetBaseline}
            onChange={(e) => setTargetBaseline(e.target.value)}
            helperText="Used to compute supplier variance and cost savings."
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Bid Submission Deadline"
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            required
          />

          <Select
            label="Target Delivery Facility"
            options={[
              { value: 'plant_a', label: 'Plant A — Midwest CNC Facility' },
              { value: 'plant_b', label: 'Plant B — Electronics Assembly' },
              { value: 'central_warehouse', label: 'Central Distribution Depot' },
            ]}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Procurement Scope & Quality Standards
          </label>
          <textarea
            rows={3}
            placeholder="Specify ISO tolerances, material certificates (CoC, Mill Test Reports), surface finishes, packaging..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-lg text-sm bg-white border border-slate-300 p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
          />
        </div>
      </form>
    </Modal>
  );
};
