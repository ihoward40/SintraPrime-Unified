import { supabase } from '../config/supabase';
import { 
  CreateBeneficiaryInput, 
  UpdateBeneficiaryInput, 
  ListBeneficiariesQuery 
} from '../models/beneficiary.schema';
import { AppError } from '../middleware/errorHandler';

export class BeneficiaryService {
  async list(query: ListBeneficiariesQuery) {
    const { page, limit, sortBy, sortOrder, search } = query;
    const offset = (page - 1) * limit;

    let queryBuilder = supabase
      .from('beneficiaries')
      .select('*', { count: 'exact' });

    if (search) {
      queryBuilder = queryBuilder.or(
        `first_name.ilike.%${search}%,last_name.ilike.%${search}%,email.ilike.%${search}%`
      );
    }

    const { data, error, count } = await queryBuilder
      .order(sortBy, { ascending: sortOrder === 'asc' })
      .range(offset, offset + limit - 1);

    if (error) {
      throw new AppError(500, `Failed to fetch beneficiaries: ${error.message}`);
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
      .from('beneficiaries')
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        throw new AppError(404, 'Beneficiary not found');
      }
      throw new AppError(500, `Failed to fetch beneficiary: ${error.message}`);
    }

    return data;
  }

  async create(input: CreateBeneficiaryInput) {
    const { data, error } = await supabase
      .from('beneficiaries')
      .insert(input)
      .select()
      .single();

    if (error) {
      throw new AppError(500, `Failed to create beneficiary: ${error.message}`);
    }

    return data;
  }

  async update(id: string, input: UpdateBeneficiaryInput) {
    const { data, error } = await supabase
      .from('beneficiaries')
      .update(input)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        throw new AppError(404, 'Beneficiary not found');
      }
      throw new AppError(500, `Failed to update beneficiary: ${error.message}`);
    }

    return data;
  }

  async delete(id: string) {
    const { error } = await supabase
      .from('beneficiaries')
      .delete()
      .eq('id', id);

    if (error) {
      throw new AppError(500, `Failed to delete beneficiary: ${error.message}`);
    }

    return { success: true };
  }
}
