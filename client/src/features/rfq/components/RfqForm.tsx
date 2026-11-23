import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { rfqFormSchema, type RfqFormValues } from '../schemas/rfqSchema';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../../components/ui/Card';
import { Save, X } from 'lucide-react';

interface RfqFormProps {
  initialValues?: Partial<RfqFormValues>;
  onSubmit: (values: RfqFormValues) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  mode: 'create' | 'edit';
}

export const RfqForm: React.FC<RfqFormProps> = ({
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting = false,
  mode,
}) => {
  const defaultValues: RfqFormValues = {
    title: initialValues?.title || '',
    rfqNumber: initialValues?.rfqNumber || '',
    description: initialValues?.description || '',
    requiredDeliveryDate:
      initialValues?.requiredDeliveryDate ||
      new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    currency: initialValues?.currency || 'USD',
    status: initialValues?.status || 'draft',
    notes: initialValues?.notes || '',
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RfqFormValues>({
    resolver: zodResolver(rfqFormSchema),
    defaultValues,
  });

  return (
    <Card className="max-w-3xl mx-auto shadow-sm">
      <CardHeader>
        <CardTitle>{mode === 'create' ? 'Create New RFQ' : 'Edit RFQ Details'}</CardTitle>
        <CardDescription>
          {mode === 'create'
            ? 'Define procurement requirements and delivery schedule before collecting supplier quotes.'
            : 'Update requirement parameters, terms, or procurement lifecycle status.'}
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-5">
          {/* Row 1: Title & Number */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <Input
                label="RFQ Title"
                placeholder="e.g. CNC Machined 6061-T6 Aluminum Housings"
                required
                error={errors.title?.message}
                {...register('title')}
              />
            </div>
            <div>
              <Input
                label="RFQ Number"
                placeholder="Auto-assigned if blank"
                helperText="Optional: auto-assigned if empty"
                error={errors.rfqNumber?.message}
                {...register('rfqNumber')}
              />
            </div>
          </div>

          {/* Row 2: Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              RFQ Description & Scope <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              placeholder="Detailed description of components, manufacturing standards, quality requirements, and target volumes..."
              className={`w-full rounded-lg text-sm bg-white border p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-offset-0 transition-colors ${
                errors.description
                  ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-200'
                  : 'border-slate-300 focus:border-slate-800 focus:ring-slate-900/10'
              }`}
              {...register('description')}
            />
            {errors.description ? (
              <p className="mt-1 text-xs text-rose-600 font-medium">{errors.description.message}</p>
            ) : (
              <p className="mt-1 text-xs text-slate-400">Brief summary displayed to suppliers and procurement reviewers.</p>
            )}
          </div>

          {/* Row 3: Delivery Date, Currency & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <Input
                label="Required Delivery Date"
                type="date"
                required
                error={errors.requiredDeliveryDate?.message}
                {...register('requiredDeliveryDate')}
              />
            </div>

            <div>
              <Select
                label="Currency"
                error={errors.currency?.message}
                options={[
                  { value: 'USD', label: 'USD ($) — US Dollar' },
                  { value: 'EUR', label: 'EUR (€) — Euro' },
                  { value: 'GBP', label: 'GBP (£) — British Pound' },
                  { value: 'CAD', label: 'CAD ($) — Canadian Dollar' },
                  { value: 'JPY', label: 'JPY (¥) — Japanese Yen' },
                ]}
                {...register('currency')}
              />
            </div>

            <div>
              <Select
                label="Lifecycle Status"
                error={errors.status?.message}
                options={[
                  { value: 'draft', label: 'Draft' },
                  { value: 'open', label: 'Open for Bids' },
                  { value: 'under_review', label: 'Under Review' },
                  { value: 'awarded', label: 'Awarded' },
                  { value: 'closed', label: 'Closed' },
                ]}
                {...register('status')}
              />
            </div>
          </div>

          {/* Row 4: Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Procurement Terms & Special Notes
            </label>
            <textarea
              rows={3}
              placeholder="e.g. Payment terms Net 30, Incoterms DAP Midwest Plant, CoC and Mill Test Reports required with each shipment."
              className="w-full rounded-lg text-sm bg-white border border-slate-300 p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
              {...register('notes')}
            />
            {errors.notes && (
              <p className="mt-1 text-xs text-rose-600 font-medium">{errors.notes.message}</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isSubmitting}
            leftIcon={<X className="w-4 h-4" />}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isSubmitting}
            leftIcon={<Save className="w-4 h-4" />}
          >
            {mode === 'create' ? 'Save RFQ' : 'Update RFQ'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
