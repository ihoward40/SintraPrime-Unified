import { Router } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import * as beneficiaryController from '../controllers/beneficiary.controller';

const router = Router();

router.get('/', asyncHandler(beneficiaryController.listBeneficiaries));
router.get('/:id', asyncHandler(beneficiaryController.getBeneficiary));
router.post('/', asyncHandler(beneficiaryController.createBeneficiary));
router.put('/:id', asyncHandler(beneficiaryController.updateBeneficiary));
router.delete('/:id', asyncHandler(beneficiaryController.deleteBeneficiary));

export default router;
