import { Request, Response } from 'express';
import { CreditDisputeService } from '../services/creditDispute.service';
import { 
  createCreditDisputeSchema, 
  updateCreditDisputeSchema, 
  listCreditDisputesQuerySchema 
} from '../models/creditDispute.schema';

const creditDisputeService = new CreditDisputeService();

export const listCreditDisputes = async (req: Request, res: Response) => {
  const query = listCreditDisputesQuerySchema.parse(req.query);
  const result = await creditDisputeService.list(query);
  res.json(result);
};

export const getCreditDispute = async (req: Request, res: Response) => {
  const { id } = req.params;
  const dispute = await creditDisputeService.getById(id);
  res.json(dispute);
};

export const createCreditDispute = async (req: Request, res: Response) => {
  const input = createCreditDisputeSchema.parse(req.body);
  const dispute = await creditDisputeService.create(input);
  res.status(201).json(dispute);
};

export const updateCreditDispute = async (req: Request, res: Response) => {
  const { id } = req.params;
  const input = updateCreditDisputeSchema.parse(req.body);
  const dispute = await creditDisputeService.update(id, input);
  res.json(dispute);
};

export const deleteCreditDispute = async (req: Request, res: Response) => {
  const { id } = req.params;
  await creditDisputeService.delete(id);
  res.status(204).send();
};
