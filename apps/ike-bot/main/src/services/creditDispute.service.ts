import { supabase } from '../config/supabase';
import { 
  CreateCreditDisputeInput, 
  UpdateCreditDisputeInput, 
  ListCreditDisputesQuery 
} from '../models/creditDispute.schema';
import { AppError } from '../middleware/errorHandler';

export class CreditDisputeService {
  async list(query: ListCreditDisputesQuery) {
    const { page, limit, sortBy, sortOrder, status, beneficiary_id } = query;
    const offset = (page - 1) * limit;

    let queryBuilder = supabase
      .from('credit_disputes')
      .select('*', { count: 'exact' });

    if (status) {
      queryBuilder = queryBuilder.eq('status', status);
    }

    if (beneficiary_id) {
      queryBuilder = queryBuilder.eq('beneficiary_id', beneficiary_id);
    }

    const { data, error, count } = await queryBuilder
      .order(sortBy, { ascending: sortOrder === 'asc' })
      .range(offset, offset + limit - 1);

    if (error) {
      throw new AppError(500, `Failed to fetch credit disputes: ${error.message}`);
    }

    return {
      data: data || [],
      pagination: {
        page,
        limit,
        total: count || 0,
        totalPages: Math.ceil((count || 0) / limit)
      }
    };
  }

  async getById(id: string) {
    const { data, error } = await supabase
      .from('credit_disputes')
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        throw new AppError(404, 'Credit dispute not found');
      }
      throw new AppError(500, `Failed to fetch credit dispute: ${error.message}`);
    }

    return data;
  }

  async create(input: CreateCreditDisputeInput) {
    const { data, error } = await supabase
      .from('credit_disputes')
      .insert(input)
      .select()
      .single();

    if (error) {
      throw new AppError(500, `Failed to create credit dispute: ${error.message}`);
    }

    return data;
  }

  async update(id: string, input: UpdateCreditDisputeInput) {
    const { data, error } = await supabase
      .from('credit_disputes')
      .update(input)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        throw new AppError(404, 'Credit dispute not found');
      }
      throw new AppError(500, `Failed to update credit dispute: ${error.message}`);
    }

    return data;
  }

  async delete(id: string) {
    const { error } = await supabase
      .from('credit_disputes')
      .delete()
      .eq('id', id);

    if (error) {
      throw new AppError(500, `Failed to delete credit dispute: ${error.message}`);
    }

    return { success: true };
  }
}
