import { Router } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import * as creditDisputeController from '../controllers/creditDispute.controller';

const router = Router();

router.get('/', asyncHandler(creditDisputeController.listCreditDisputes));
router.get('/:id', asyncHandler(creditDisputeController.getCreditDispute));
router.post('/', asyncHandler(creditDisputeController.createCreditDispute));
router.put('/:id', asyncHandler(creditDisputeController.updateCreditDispute));
router.delete('/:id', asyncHandler(creditDisputeController.deleteCreditDispute));

export default router;
