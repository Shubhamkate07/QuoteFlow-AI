import { z } from 'zod';

export const rfqFormSchema = z.object({
  title: z
    .string()
    .min(3, 'RFQ title must be at least 3 characters')
    .max(120, 'RFQ title must not exceed 120 characters'),
  rfqNumber: z
    .string()
    .optional()
    .refine((val) => !val || /^RFQ-[0-9]{4}-[0-9]{3,6}$/i.test(val), {
      message: 'Format must match RFQ-YYYY-XXX (e.g. RFQ-2026-001 or RFQ-2026-0045)',
    }),
  description: z
    .string()
    .max(1000, 'Description must not exceed 1000 characters')
    .optional(),
  requiredDeliveryDate: z
    .string()
    .optional()
    .refine((val) => !val || !isNaN(Date.parse(val)), 'Invalid date format'),
  currency: z.enum(['USD', 'EUR', 'GBP', 'CAD', 'JPY'], {
    message: 'Please select a valid currency',
  }),
  status: z.enum(['draft', 'open', 'under_review', 'awarded', 'closed'], {
    message: 'Please select a valid status',
  }),
  notes: z.string().max(2000, 'Notes must not exceed 2000 characters').optional(),
});

export type RfqFormValues = z.infer<typeof rfqFormSchema>;

export const rfqItemSchema = z.object({
  name: z
    .string()
    .min(2, 'Item name must be at least 2 characters')
    .max(250, 'Item name must not exceed 250 characters'),
  description: z.string().max(5000, 'Description must not exceed 5000 characters').optional(),
  quantity: z
    .number({ message: 'Quantity is required' })
    .positive('Quantity must be greater than 0'),
  unit: z.string().min(1, 'Unit of measure is required'),
  targetUnitPrice: z
    .number()
    .min(0, 'Target price must be positive')
    .optional(),
  requiredSpecifications: z
    .string()
    .max(5000, 'Specifications must not exceed 5000 characters')
    .optional(),
  manufacturerPreference: z.string().max(250).optional(),
  modelPreference: z.string().max(250).optional(),
  requiredDeliveryDate: z.string().optional(),
  notes: z.string().max(5000, 'Notes must not exceed 5000 characters').optional(),
  specsList: z
    .array(
      z.object({
        key: z.string().optional(),
        value: z.string().optional(),
      })
    )
    .optional(),
});

export type RfqItemFormValues = z.infer<typeof rfqItemSchema>;
