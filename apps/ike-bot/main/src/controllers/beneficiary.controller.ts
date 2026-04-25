import { Request, Response } from 'express';
import { BeneficiaryService } from '../services/beneficiary.service';
import { 
  createBeneficiarySchema, 
  updateBeneficiarySchema, 
  listBeneficiariesQuerySchema 
} from '../models/beneficiary.schema';

const beneficiaryService = new BeneficiaryService();

export const listBeneficiaries = async (req: Request, res: Response) => {
  const query = listBeneficiariesQuerySchema.parse(req.query);
  const result = await beneficiaryService.list(query);
  res.json(result);
};

export const getBeneficiary = async (req: Request, res: Response) => {
  const { id } = req.params;
  const beneficiary = await beneficiaryService.getById(id);
  res.json(beneficiary);
};

export const createBeneficiary = async (req: Request, res: Response) => {
  const input = createBeneficiarySchema.parse(req.body);
  const beneficiary = await beneficiaryService.create(input);
  res.status(201).json(beneficiary);
};

export const updateBeneficiary = async (req: Request, res: Response) => {
  const { id } = req.params;
  const input = updateBeneficiarySchema.parse(req.body);
  const beneficiary = await beneficiaryService.update(id, input);
  res.json(beneficiary);
};

export const deleteBeneficiary = async (req: Request, res: Response) => {
  const { id } = req.params;
  await beneficiaryService.delete(id);
  res.status(204).send();
};
