import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { rfqItemSchema, type RfqItemFormValues } from '../schemas/rfqSchema';
import type { RfqItem } from '../types';
import { Modal } from '../../../components/ui/Modal';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import { Plus, Trash2, SlidersHorizontal, PackageCheck, AlertCircle } from 'lucide-react';

interface RfqItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (values: RfqItemFormValues) => void;
  initialItem?: RfqItem | null;
  currency?: string;
  defaultDeliveryDate?: string;
  isSubmitting?: boolean;
}

export const RfqItemModal: React.FC<RfqItemModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialItem,
  currency = 'USD',
  defaultDeliveryDate,
  isSubmitting = false,
}) => {
  const [activeTab, setActiveTab] = useState<'details' | 'specs' | 'preferences'>('details');

  const defaultValues: RfqItemFormValues = {
    name: initialItem?.name || '',
    description: initialItem?.description || '',
    quantity: initialItem?.quantity || 100,
    unit: initialItem?.unit || 'PCS',
    targetUnitPrice: initialItem?.targetUnitPrice || undefined,
    requiredSpecifications: initialItem?.requiredSpecifications || '',
    manufacturerPreference: initialItem?.manufacturerPreference || '',
    modelPreference: initialItem?.modelPreference || '',
    requiredDeliveryDate: initialItem?.requiredDeliveryDate || defaultDeliveryDate || '',
    notes: initialItem?.notes || '',
    specsList: initialItem?.specsList || [
      { key: 'Material', value: '' },
      { key: 'Tolerance', value: '' },
    ],
  };

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<RfqItemFormValues>({
    resolver: zodResolver(rfqItemSchema),
    defaultValues,
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'specsList',
  });

  const isEdit = Boolean(initialItem);

  const hasDetailsErrors = Boolean(
    errors.name || errors.quantity || errors.unit || errors.targetUnitPrice || errors.description
  );
  const hasSpecsErrors = Boolean(errors.requiredSpecifications || errors.specsList);
  const hasPrefErrors = Boolean(
    errors.manufacturerPreference || errors.modelPreference || errors.requiredDeliveryDate || errors.notes
  );

  const onInvalid = (formErrors: any) => {
    if (formErrors.name || formErrors.quantity || formErrors.unit || formErrors.targetUnitPrice || formErrors.description) {
      setActiveTab('details');
    } else if (formErrors.requiredSpecifications || formErrors.specsList) {
      setActiveTab('specs');
    } else if (formErrors.manufacturerPreference || formErrors.modelPreference || formErrors.requiredDeliveryDate || formErrors.notes) {
      setActiveTab('preferences');
    }
  };

  const handleFormSubmit = (values: RfqItemFormValues) => {
    const cleanedSpecs = (values.specsList || []).filter(
      (s) => (s.key && s.key.trim().length > 0) || (s.value && s.value.trim().length > 0)
    );
    onSubmit({ ...values, specsList: cleanedSpecs });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Line Item: ${initialItem?.itemNumber || initialItem?.name}` : 'Add Required RFQ Item'}
      description="Define the component specifications, quantity, and preferences for supplier quote comparison."
      maxWidth="xl"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit(handleFormSubmit, onInvalid)}
            isLoading={isSubmitting}
            leftIcon={<PackageCheck className="w-4 h-4" />}
          >
            {isEdit ? 'Update Item' : 'Add Item to RFQ'}
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Validation Errors Global Banner */}
        {Object.keys(errors).length > 0 && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold">Please resolve the following before saving:</span>
              <ul className="list-disc list-inside mt-1 text-[11px] text-rose-700 space-y-0.5">
                {Object.entries(errors).map(([k, err]) => (
                  <li key={k}>{err?.message || `${k} is invalid`}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 gap-4 text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('details')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 flex items-center gap-1.5 ${
              activeTab === 'details'
                ? 'border-slate-900 text-slate-900 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>1. Basic Information</span>
            {hasDetailsErrors && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('specs')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 flex items-center gap-1.5 ${
              activeTab === 'specs'
                ? 'border-slate-900 text-slate-900 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>2. Required Specifications</span>
            {hasSpecsErrors && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('preferences')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 flex items-center gap-1.5 ${
              activeTab === 'preferences'
                ? 'border-slate-900 text-slate-900 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>3. Preferences & Logistics</span>
            {hasPrefErrors && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
          </button>
        </div>

        {/* Tab 1: Basic Information */}
        {activeTab === 'details' && (
          <div className="space-y-4 animate-in fade-in duration-150">
            <Input
              label="Item Name / Part Name"
              placeholder="e.g. Milled Upper Electronics Housing"
              required
              error={errors.name?.message}
              {...register('name')}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <Input
                  label="Required Quantity"
                  type="number"
                  placeholder="500"
                  required
                  error={errors.quantity?.message}
                  {...register('quantity', { valueAsNumber: true })}
                />
              </div>

              <div>
                <Select
                  label="Unit of Measure (UOM)"
                  error={errors.unit?.message}
                  options={[
                    { value: 'PCS', label: 'PCS (Pieces)' },
                    { value: 'SET', label: 'SET (Assembly Set)' },
                    { value: 'KG', label: 'KG (Kilograms)' },
                    { value: 'M', label: 'M (Meters)' },
                    { value: 'LOT', label: 'LOT (Entire Lot)' },
                    { value: 'ROLL', label: 'ROLL (Rolls)' },
                  ]}
                  {...register('unit')}
                />
              </div>

              <div>
                <Input
                  label={`Target Unit Price (${currency})`}
                  type="number"
                  step="0.01"
                  placeholder="22.50"
                  error={errors.targetUnitPrice?.message}
                  {...register('targetUnitPrice', { valueAsNumber: true })}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-semibold text-slate-700">
                  Item Description / Manufacturing Function
                </label>
                <span className="text-[10px] text-slate-400">Max 5,000 chars</span>
              </div>
              <textarea
                rows={3}
                placeholder="Brief summary of what this component does, mating parts, or special handling..."
                className="w-full rounded-lg text-sm bg-white border border-slate-300 p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
                {...register('description')}
              />
              {errors.description && (
                <p className="mt-1 text-xs text-rose-600 font-medium">{errors.description.message}</p>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Required Specifications */}
        {activeTab === 'specs' && (
          <div className="space-y-4 animate-in fade-in duration-150">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Primary Specification Summary <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                placeholder="e.g. AL 6061-T6, Clear Anodized Type II Class 1, Dimensions 180x120x35mm, Critical Tolerance ±0.025mm..."
                className={`w-full rounded-lg text-sm bg-white border p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-offset-0 transition-colors ${
                  errors.requiredSpecifications
                    ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-200'
                    : 'border-slate-300 focus:border-slate-800 focus:ring-slate-900/10'
                }`}
                {...register('requiredSpecifications')}
              />
              {errors.requiredSpecifications ? (
                <p className="mt-1 text-xs text-rose-600 font-medium">
                  {errors.requiredSpecifications.message}
                </p>
              ) : (
                <p className="mt-1 text-xs text-slate-500">
                  QuoteFlow AI compares vendor quotation descriptions against these specifications to spot material substitutions and dimension discrepancies.
                </p>
              )}
            </div>

            {/* Flexible Key-Value Parameter Builder */}
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center space-x-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-xs font-semibold text-slate-800">
                    Structured Specification Attributes (Optional)
                  </span>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => append({ key: '', value: '' })}
                  className="h-7 text-xs px-2 gap-1"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Attribute</span>
                </Button>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {fields.map((field, idx) => (
                  <div key={field.id} className="flex items-center gap-2">
                    <input
                      placeholder="e.g. Material / Tolerance / Finish"
                      className="w-1/3 px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800"
                      {...register(`specsList.${idx}.key` as const)}
                    />
                    <input
                      placeholder="e.g. Aluminum 6061-T6 / ±0.05 mm"
                      className="flex-1 px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800"
                      {...register(`specsList.${idx}.value` as const)}
                    />
                    <button
                      type="button"
                      onClick={() => remove(idx)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md transition-colors"
                      title="Remove attribute"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Preferences & Logistics */}
        {activeTab === 'preferences' && (
          <div className="space-y-4 animate-in fade-in duration-150">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Manufacturer Preference"
                placeholder="e.g. Fastenal, Misumi, or Approved Equal"
                helperText="Specify if a specific brand or ISO certification is preferred."
                {...register('manufacturerPreference')}
              />

              <Input
                label="Model / Catalog Part Number"
                placeholder="e.g. DIN-912-M4-16 or Custom Drawing #REV-C"
                helperText="Original equipment manufacturer (OEM) part code."
                {...register('modelPreference')}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Item-specific Delivery Milestone"
                type="date"
                helperText="Leave empty to use the master RFQ delivery date."
                {...register('requiredDeliveryDate')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Item Notes & Inspection Criteria
              </label>
              <textarea
                rows={2}
                placeholder="e.g. Certificate of Conformance (CoC), lot traceability, cleanroom packaging required..."
                className="w-full rounded-lg text-sm bg-white border border-slate-300 p-2.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
                {...register('notes')}
              />
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
