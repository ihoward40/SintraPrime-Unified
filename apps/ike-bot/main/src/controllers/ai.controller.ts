/**
 * AI Controller
 * 
 * Handles AI-powered API endpoints for IkeBot
 */

import { Request, Response } from 'express';
import { z } from 'zod';
import { isOpenAIAvailable } from '../ai/client';
import { generateText, generateStructured } from '../ai/services/textGeneration';
import { generateImage, generateDocumentAsset } from '../ai/services/imageGeneration';
import {
  getBeneficiaryAnalysisPrompt,
  getPortfolioAnalysisPrompt,
  getRiskAssessmentPrompt,
  getPersonalizedMessagePrompt,
} from '../ai/prompts/beneficiary';
import {
  getDisputeLetterPrompt,
  getDisputeAnalysisPrompt,
  getSuccessProbabilityPrompt,
} from '../ai/prompts/dispute';
import { logger } from '../config/logger';

/**
 * Check if AI features are available
 */
export async function checkAIStatus(req: Request, res: Response) {
  try {
    const available = isOpenAIAvailable();
    
    res.json({
      available,
      message: available 
        ? 'AI features are enabled' 
        : 'AI features are disabled. Configure OPENAI_API_KEY to enable.',
    });
  } catch (error: any) {
    logger.error('Error checking AI status:', error);
    res.status(500).json({ error: 'Failed to check AI status' });
  }
}

/**
 * Analyze a beneficiary
 */
export async function analyzeBeneficiary(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const beneficiarySchema = z.object({
      id: z.string(),
      first_name: z.string(),
      last_name: z.string(),
      email: z.string().email(),
      phone: z.string().optional(),
      relationship: z.string(),
      created_at: z.string(),
      credit_disputes: z.array(z.any()).optional(),
      billing_events: z.array(z.any()).optional(),
    });

    const beneficiary = beneficiarySchema.parse(req.body);
    const prompt = getBeneficiaryAnalysisPrompt(beneficiary);

    const result = await generateText(prompt, {
      model: 'gpt-5',
      temperature: 0.7,
      instructions: 'You are a professional case manager analyzing beneficiary profiles.',
    });

    res.json({
      beneficiary_id: beneficiary.id,
      analysis: result.text,
      tokens_used: result.tokensUsed,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error analyzing beneficiary:', error);
    res.status(500).json({ error: error.message || 'Failed to analyze beneficiary' });
  }
}

/**
 * Analyze portfolio of beneficiaries
 */
export async function analyzePortfolio(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const portfolioSchema = z.object({
      beneficiaries: z.array(z.any()),
    });

    const { beneficiaries } = portfolioSchema.parse(req.body);
    const prompt = getPortfolioAnalysisPrompt(beneficiaries);

    const result = await generateText(prompt, {
      model: 'gpt-5',
      temperature: 0.7,
      instructions: 'You are a senior case manager providing executive-level portfolio analysis.',
    });

    res.json({
      portfolio_size: beneficiaries.length,
      analysis: result.text,
      tokens_used: result.tokensUsed,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error analyzing portfolio:', error);
    res.status(500).json({ error: error.message || 'Failed to analyze portfolio' });
  }
}

/**
 * Generate dispute letter
 */
export async function generateDisputeLetter(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const requestSchema = z.object({
      dispute: z.object({
        id: z.string(),
        beneficiary_id: z.string(),
        creditor_name: z.string(),
        dispute_reason: z.string(),
        dispute_type: z.enum(['identity_theft', 'not_mine', 'inaccurate', 'duplicate', 'paid', 'other']),
        status: z.string(),
        account_number: z.string().optional(),
        amount: z.number().optional(),
        date_opened: z.string().optional(),
      }),
      beneficiary: z.object({
        first_name: z.string(),
        last_name: z.string(),
        email: z.string().email(),
        phone: z.string().optional(),
        address: z.string().optional(),
      }),
    });

    const { dispute, beneficiary } = requestSchema.parse(req.body);
    const prompt = getDisputeLetterPrompt(dispute, beneficiary);

    const result = await generateText(prompt, {
      model: 'gpt-5',
      temperature: 0.5, // Lower temperature for more consistent legal language
      instructions: 'You are a legal document specialist creating formal credit dispute letters.',
    });

    res.json({
      dispute_id: dispute.id,
      letter: result.text,
      tokens_used: result.tokensUsed,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error generating dispute letter:', error);
    res.status(500).json({ error: error.message || 'Failed to generate dispute letter' });
  }
}

/**
 * Analyze dispute success probability
 */
export async function analyzeDisputeSuccess(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const disputeSchema = z.object({
      id: z.string(),
      creditor_name: z.string(),
      dispute_reason: z.string(),
      dispute_type: z.enum(['identity_theft', 'not_mine', 'inaccurate', 'duplicate', 'paid', 'other']),
    });

    const dispute = disputeSchema.parse(req.body);
    const prompt = getSuccessProbabilityPrompt(dispute as any);

    const result = await generateText(prompt, {
      model: 'gpt-5',
      temperature: 0.3, // Lower temperature for more consistent analysis
      instructions: 'You are a credit dispute expert providing probability assessments.',
    });

    res.json({
      dispute_id: dispute.id,
      analysis: result.text,
      tokens_used: result.tokensUsed,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error analyzing dispute:', error);
    res.status(500).json({ error: error.message || 'Failed to analyze dispute' });
  }
}

/**
 * Generate document asset (image)
 */
export async function generateAsset(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const requestSchema = z.object({
      asset_type: z.enum(['letterhead', 'logo', 'diagram', 'chart']),
      description: z.string(),
      size: z.enum(['1024x1024', '1792x1024', '1024x1792']).optional(),
      quality: z.enum(['standard', 'hd']).optional(),
    });

    const { asset_type, description, size, quality } = requestSchema.parse(req.body);

    const result = await generateDocumentAsset(asset_type, description, {
      size,
      quality,
    });

    // Return image as base64 or URL
    res.json({
      asset_type,
      image_url: result.imageUrl,
      image_data: result.imageData?.toString('base64'),
      revised_prompt: result.revisedPrompt,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error generating asset:', error);
    res.status(500).json({ error: error.message || 'Failed to generate asset' });
  }
}

/**
 * Generate personalized message
 */
export async function generateMessage(req: Request, res: Response) {
  try {
    if (!isOpenAIAvailable()) {
      return res.status(503).json({ error: 'AI features are not available' });
    }

    const requestSchema = z.object({
      beneficiary: z.object({
        first_name: z.string(),
        last_name: z.string(),
        email: z.string().email(),
      }),
      message_type: z.enum(['welcome', 'update', 'alert', 'reminder']),
      context: z.string().optional(),
    });

    const { beneficiary, message_type, context } = requestSchema.parse(req.body);
    const prompt = getPersonalizedMessagePrompt(beneficiary as any, message_type, context);

    const result = await generateText(prompt, {
      model: 'gpt-5',
      temperature: 0.8, // Higher temperature for more creative messaging
      maxTokens: 500,
    });

    res.json({
      message: result.text,
      tokens_used: result.tokensUsed,
      cost_usd: result.costUsd,
      model: result.model,
    });
  } catch (error: any) {
    logger.error('Error generating message:', error);
    res.status(500).json({ error: error.message || 'Failed to generate message' });
  }
}
