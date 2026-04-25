/**
 * AI Routes
 * 
 * API routes for AI-powered features
 */

import { Router } from 'express';
import * as aiController from '../controllers/ai.controller';

const router = Router();

/**
 * @route   GET /api/ai/status
 * @desc    Check if AI features are available
 * @access  Public
 */
router.get('/status', aiController.checkAIStatus);

/**
 * @route   POST /api/ai/analyze-beneficiary
 * @desc    Analyze a single beneficiary
 * @access  Private
 * @body    { beneficiary: BeneficiaryData }
 */
router.post('/analyze-beneficiary', aiController.analyzeBeneficiary);

/**
 * @route   POST /api/ai/analyze-portfolio
 * @desc    Analyze portfolio of beneficiaries
 * @access  Private
 * @body    { beneficiaries: BeneficiaryData[] }
 */
router.post('/analyze-portfolio', aiController.analyzePortfolio);

/**
 * @route   POST /api/ai/generate-dispute-letter
 * @desc    Generate credit dispute letter
 * @access  Private
 * @body    { dispute: DisputeData, beneficiary: BeneficiaryInfo }
 */
router.post('/generate-dispute-letter', aiController.generateDisputeLetter);

/**
 * @route   POST /api/ai/analyze-dispute
 * @desc    Analyze dispute success probability
 * @access  Private
 * @body    { dispute: DisputeData }
 */
router.post('/analyze-dispute', aiController.analyzeDisputeSuccess);

/**
 * @route   POST /api/ai/generate-asset
 * @desc    Generate document asset (image)
 * @access  Private
 * @body    { asset_type, description, size?, quality? }
 */
router.post('/generate-asset', aiController.generateAsset);

/**
 * @route   POST /api/ai/generate-message
 * @desc    Generate personalized message
 * @access  Private
 * @body    { beneficiary, message_type, context? }
 */
router.post('/generate-message', aiController.generateMessage);

export default router;
