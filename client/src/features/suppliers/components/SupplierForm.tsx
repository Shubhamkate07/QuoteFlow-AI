import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { supplierSchema, type SupplierFormValues } from '../schemas/supplierSchema';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../../components/ui/Card';
import { Save, X, Building2, Mail, Phone, Globe, Hash, MapPin } from 'lucide-react';

interface SupplierFormProps {
  initialValues?: Partial<SupplierFormValues>;
  onSubmit: (values: SupplierFormValues) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  mode: 'create' | 'edit';
}

export const SupplierForm: React.FC<SupplierFormProps> = ({
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting = false,
  mode,
}) => {
  const defaultValues: SupplierFormValues = {
    companyName: initialValues?.companyName || '',
    contactPerson: initialValues?.contactPerson || '',
    email: initialValues?.email || '',
    phone: initialValues?.phone || '',
    address: initialValues?.address || '',
    country: initialValues?.country || 'US',
    gstVatNumber: initialValues?.gstVatNumber || '',
    website: initialValues?.website || '',
    category: initialValues?.category || 'machining',
    notes: initialValues?.notes || '',
    status: initialValues?.status || 'active',
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SupplierFormValues>({
    resolver: zodResolver(supplierSchema),
    defaultValues,
  });

  return (
    <Card className="max-w-3xl mx-auto shadow-sm">
      <CardHeader>
        <CardTitle>{mode === 'create' ? 'Register New Supplier' : 'Edit Supplier Profile'}</CardTitle>
        <CardDescription>
          Maintain vendor contact information, tax IDs, country of origin, and manufacturing capabilities.
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {/* Row 1: Company & Contact */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Company Name"
              placeholder="e.g. Apex Precision Machining Inc."
              required
              leftIcon={<Building2 className="w-4 h-4" />}
              error={errors.companyName?.message}
              {...register('companyName')}
            />

            <Input
              label="Primary Contact Person"
              placeholder="e.g. David Miller"
              required
              error={errors.contactPerson?.message}
              {...register('contactPerson')}
            />
          </div>

          {/* Row 2: Email & Phone */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Business Email"
              type="email"
              placeholder="quotes@apexmachining.com"
              required
              leftIcon={<Mail className="w-4 h-4" />}
              error={errors.email?.message}
              {...register('email')}
            />

            <Input
              label="Phone Number"
              placeholder="+1 (555) 382-9910"
              required
              leftIcon={<Phone className="w-4 h-4" />}
              error={errors.phone?.message}
              {...register('phone')}
            />
          </div>

          {/* Row 3: Physical Address & Country */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Physical Facility / Dispatch Address"
                placeholder="Street address, City, State, Postal Code"
                required
                leftIcon={<MapPin className="w-4 h-4" />}
                error={errors.address?.message}
                {...register('address')}
              />
            </div>
            <div>
              <Input
                label="Country"
                placeholder="e.g. US, DE, CN, IN, GB"
                required
                error={errors.country?.message}
                {...register('country')}
              />
            </div>
          </div>

          {/* Row 4: Tax ID & Website */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="GST / VAT / Tax ID"
              placeholder="e.g. US-EIN-384910284 or DE-VAT-284910294"
              leftIcon={<Hash className="w-4 h-4" />}
              error={errors.gstVatNumber?.message}
              {...register('gstVatNumber')}
            />

            <Input
              label="Company Website"
              placeholder="https://supplier.example.com"
              leftIcon={<Globe className="w-4 h-4" />}
              error={errors.website?.message}
              {...register('website')}
            />
          </div>

          {/* Row 5: Category & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Primary Manufacturing Category"
              error={errors.category?.message}
              options={[
                { value: 'machining', label: 'CNC Machining & Milling' },
                { value: 'fasteners', label: 'Hardware & Fasteners' },
                { value: 'sheet_metal', label: 'Sheet Metal Fabrication' },
                { value: 'plastics', label: 'Injection Molding & Polymers' },
                { value: 'electronics', label: 'Electronics & Wire Harnesses' },
                { value: 'surface_treatment', label: 'Surface Treatment & Anodizing' },
                { value: 'raw_materials', label: 'Raw Bar & Plate Stock' },
                { value: 'other', label: 'Other Manufacturing Services' },
              ]}
              {...register('category')}
            />

            <Select
              label="Vendor Lifecycle Status"
              error={errors.status?.message}
              options={[
                { value: 'active', label: 'Active Vendor (Eligible for RFQs)' },
                { value: 'pending', label: 'Pending Onboarding Review' },
                { value: 'inactive', label: 'Inactive / On Hold' },
              ]}
              {...register('status')}
            />
          </div>

          {/* Row 6: Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Certifications & Supplier Notes
            </label>
            <textarea
              rows={3}
              placeholder="Specify quality accreditations (ISO 9001, AS9100), typical lead times, payment terms, or machine capabilities..."
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
            {mode === 'create' ? 'Register Supplier' : 'Save Changes'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
