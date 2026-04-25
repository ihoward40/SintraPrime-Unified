import { z } from 'zod';

export const beneficiarySchema = z.object({
  id: z.string().uuid().optional(),
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  email: z.string().email('Invalid email format').optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  ssn_last_four: z.string().length(4, 'SSN must be last 4 digits').optional(),
  date_of_birth: z.string().optional(),
  relationship: z.string().optional(),
  notes: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export const createBeneficiarySchema = beneficiarySchema.omit({ 
  id: true, 
  created_at: true, 
  updated_at: true 
});

export const updateBeneficiarySchema = createBeneficiarySchema.partial();

export const listBeneficiariesQuerySchema = z.object({
  page: z.string().optional().default('1').transform(Number),
  limit: z.string().optional().default('10').transform(Number),
  sortBy: z.string().optional().default('created_at'),
  sortOrder: z.enum(['asc', 'desc']).optional().default('desc'),
  search: z.string().optional(),
});

export type Beneficiary = z.infer<typeof beneficiarySchema>;
export type CreateBeneficiaryInput = z.infer<typeof createBeneficiarySchema>;
export type UpdateBeneficiaryInput = z.infer<typeof updateBeneficiarySchema>;
export type ListBeneficiariesQuery = z.infer<typeof listBeneficiariesQuerySchema>;
