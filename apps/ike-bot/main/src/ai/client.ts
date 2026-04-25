/**
 * OpenAI Client Configuration
 * 
 * Centralized OpenAI API client for IkeBot
 * Handles authentication, error handling, and logging
 */

import { OpenAI } from 'openai';
import { logger } from '../config/logger';

// Initialize OpenAI client
export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  // Optional: Use custom base URL if needed
  baseURL: process.env.OPENAI_API_BASE,
});

/**
 * Validate OpenAI configuration
 */
export function validateOpenAIConfig(): boolean {
  if (!process.env.OPENAI_API_KEY) {
    logger.warn('OPENAI_API_KEY not configured. AI features will be disabled.');
    return false;
  }
  return true;
}

/**
 * Check if OpenAI features are available
 */
export function isOpenAIAvailable(): boolean {
  return !!process.env.OPENAI_API_KEY;
}

/**
 * Calculate estimated cost for OpenAI API usage
 */
export function calculateCost(tokens: number, model: string): number {
  // Pricing as of 2026 (adjust as needed)
  const pricing: Record<string, { input: number; output: number }> = {
    'gpt-5': { input: 0.000003, output: 0.000015 },
    'gpt-5-2': { input: 0.000002, output: 0.000010 },
    'gpt-4o': { input: 0.0000025, output: 0.00001 },
    'dall-e-3': { input: 0, output: 0.04 }, // Per image
  };

  const modelPricing = pricing[model] || pricing['gpt-4o'];
  
  // Rough estimate (assuming 50/50 input/output split for text)
  if (model.startsWith('dall-e')) {
    return modelPricing.output; // Per image
  }
  
  const inputTokens = tokens * 0.5;
  const outputTokens = tokens * 0.5;
  
  return (inputTokens * modelPricing.input) + (outputTokens * modelPricing.output);
}

/**
 * Log AI operation for audit trail
 */
export interface AIOperationLog {
  operationId: string;
  type: 'text' | 'image' | 'analysis' | 'chat';
  model: string;
  prompt: string;
  response: any;
  tokensUsed?: number;
  costUsd?: number;
  beneficiaryId?: string;
  disputeId?: string;
  createdBy?: string;
  metadata?: Record<string, any>;
}

export async function logAIOperation(log: AIOperationLog): Promise<void> {
  logger.info({
    msg: 'AI operation completed',
    operationId: log.operationId,
    type: log.type,
    model: log.model,
    tokensUsed: log.tokensUsed,
    costUsd: log.costUsd,
    beneficiaryId: log.beneficiaryId,
    disputeId: log.disputeId,
  });

  // TODO: Store in database (ai_generations table)
  // This will be implemented when database integration is ready
}

/**
 * Error handling wrapper for OpenAI operations
 */
export async function withOpenAIErrorHandling<T>(
  operation: () => Promise<T>,
  operationName: string
): Promise<T> {
  try {
    return await operation();
  } catch (error: any) {
    logger.error({
      msg: `OpenAI operation failed: ${operationName}`,
      error: error.message,
      status: error.status,
      type: error.type,
    });

    // Rethrow with more context
    throw new Error(`AI operation failed: ${error.message}`);
  }
}
