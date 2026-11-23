import { z } from 'zod';

export const supplierSchema = z.object({
  companyName: z
    .string()
    .min(2, 'Company name must be at least 2 characters')
    .max(120, 'Company name must not exceed 120 characters'),
  contactPerson: z
    .string()
    .min(2, 'Contact person name is required')
    .max(80, 'Contact name must not exceed 80 characters'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  phone: z
    .string()
    .min(5, 'Phone number is required')
    .max(30, 'Phone number too long'),
  address: z
    .string()
    .min(2, 'Address must be at least 2 characters')
    .max(250, 'Address must not exceed 250 characters'),
  country: z
    .string()
    .min(1, 'Country is required')
    .max(100, 'Country name too long'),
  gstVatNumber: z
    .string()
    .max(50, 'Tax identification must not exceed 50 characters')
    .optional(),
  website: z
    .string()
    .url('Please enter a valid URL (e.g. https://supplier.com)')
    .or(z.literal(''))
    .optional(),
  category: z.enum(
    [
      'machining',
      'sheet_metal',
      'fasteners',
      'plastics',
      'electronics',
      'raw_materials',
      'surface_treatment',
      'other',
    ],
    { message: 'Please select a valid supplier category' }
  ),
  notes: z.string().max(2000, 'Notes must not exceed 2000 characters').optional(),
  status: z.enum(['active', 'pending', 'inactive']),
});

export type SupplierFormValues = z.infer<typeof supplierSchema>;
