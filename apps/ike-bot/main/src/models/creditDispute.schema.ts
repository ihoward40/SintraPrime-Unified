import { z } from 'zod';

export const creditDisputeSchema = z.object({
  id: z.string().uuid().optional(),
  beneficiary_id: z.string().uuid('Invalid beneficiary ID'),
  creditor_name: z.string().min(1, 'Creditor name is required').max(200),
  account_number: z.string().optional(),
  dispute_reason: z.string().min(1, 'Dispute reason is required'),
  dispute_type: z.enum(['identity_theft', 'not_mine', 'inaccurate', 'duplicate', 'paid', 'other']),
  status: z.enum(['pending', 'submitted', 'investigating', 'resolved', 'rejected']).default('pending'),
  amount_disputed: z.number().optional(),
  date_submitted: z.string().optional(),
  date_resolved: z.string().optional(),
  resolution_notes: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export const createCreditDisputeSchema = creditDisputeSchema.omit({ 
  id: true, 
  created_at: true, 
  updated_at: true 
});

export const updateCreditDisputeSchema = createCreditDisputeSchema.partial().omit({ beneficiary_id: true });

export const listCreditDisputesQuerySchema = z.object({
  page: z.string().optional().default('1').transform(Number),
  limit: z.string().optional().default('10').transform(Number),
  sortBy: z.string().optional().default('created_at'),
  sortOrder: z.enum(['asc', 'desc']).optional().default('desc'),
  status: z.enum(['pending', 'submitted', 'investigating', 'resolved', 'rejected']).optional(),
  beneficiary_id: z.string().uuid().optional(),
});

export type CreditDispute = z.infer<typeof creditDisputeSchema>;
export type CreateCreditDisputeInput = z.infer<typeof createCreditDisputeSchema>;
export type UpdateCreditDisputeInput = z.infer<typeof updateCreditDisputeSchema>;
export type ListCreditDisputesQuery = z.infer<typeof listCreditDisputesQuerySchema>;
