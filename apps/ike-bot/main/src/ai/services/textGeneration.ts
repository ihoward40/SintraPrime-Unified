/**
 * Text Generation Service
 * 
 * Handles all text generation operations using OpenAI API
 */

import { v4 as uuidv4 } from 'uuid';
import { openai, calculateCost, logAIOperation, withOpenAIErrorHandling } from '../client';

export interface TextGenerationOptions {
  model?: string;
  maxTokens?: number;
  temperature?: number;
  instructions?: string;
}

export interface TextGenerationResult {
  text: string;
  tokensUsed: number;
  costUsd: number;
  model: string;
}

/**
 * Generate text using OpenAI Responses API
 */
export async function generateText(
  prompt: string,
  options: TextGenerationOptions = {}
): Promise<TextGenerationResult> {
  const {
    model = 'gpt-5',
    maxTokens = 2000,
    temperature = 0.7,
    instructions,
  } = options;

  const operationId = uuidv4();

  const result = await withOpenAIErrorHandling(async () => {
    const response = await openai.responses.create({
      model,
      input: prompt,
      instructions,
      max_tokens: maxTokens,
      temperature,
    });

    const text = response.output?.[0]?.content || '';
    const tokensUsed = response.usage?.total_tokens || 0;
    const costUsd = calculateCost(tokensUsed, model);

    // Log operation
    await logAIOperation({
      operationId,
      type: 'text',
      model,
      prompt,
      response: text,
      tokensUsed,
      costUsd,
    });

    return {
      text,
      tokensUsed,
      costUsd,
      model,
    };
  }, 'generateText');

  return result;
}

/**
 * Generate text with streaming (for real-time responses)
 */
export async function* generateTextStreaming(
  prompt: string,
  options: TextGenerationOptions = {}
): AsyncGenerator<string> {
  const {
    model = 'gpt-5',
    maxTokens = 2000,
    temperature = 0.7,
    instructions,
  } = options;

  const stream = await openai.responses.create({
    model,
    input: prompt,
    instructions,
    max_tokens: maxTokens,
    temperature,
    stream: true,
  });

  for await (const chunk of stream) {
    const delta = chunk.output?.[0]?.content_delta;
    if (delta) {
      yield delta;
    }
  }
}

/**
 * Generate structured output using Pydantic-like schemas
 */
export async function generateStructured<T>(
  prompt: string,
  schema: any, // Zod schema
  options: TextGenerationOptions = {}
): Promise<T> {
  const {
    model = 'gpt-4o-2024-08-06', // Structured outputs require specific model
    instructions,
  } = options;

  const operationId = uuidv4();

  const result = await withOpenAIErrorHandling(async () => {
    const response = await openai.responses.create({
      model,
      input: prompt,
      instructions,
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: 'structured_output',
          strict: true,
          schema: schema,
        },
      },
    });

    const output = response.output?.[0]?.content || '{}';
    const parsed = JSON.parse(output);
    const tokensUsed = response.usage?.total_tokens || 0;
    const costUsd = calculateCost(tokensUsed, model);

    // Log operation
    await logAIOperation({
      operationId,
      type: 'analysis',
      model,
      prompt,
      response: parsed,
      tokensUsed,
      costUsd,
    });

    return parsed as T;
  }, 'generateStructured');

  return result;
}

/**
 * Multi-turn conversation
 */
export interface Message {
  role: 'user' | 'assistant' | 'developer';
  content: string;
}

export async function chat(
  messages: Message[],
  options: TextGenerationOptions = {}
): Promise<TextGenerationResult> {
  const {
    model = 'gpt-5',
    maxTokens = 2000,
    temperature = 0.7,
  } = options;

  const operationId = uuidv4();

  // Convert messages to OpenAI format
  const lastMessage = messages[messages.length - 1];
  const context = messages.slice(0, -1).map(m => `${m.role}: ${m.content}`).join('\n\n');
  const prompt = context ? `${context}\n\n${lastMessage.content}` : lastMessage.content;

  const result = await withOpenAIErrorHandling(async () => {
    const response = await openai.responses.create({
      model,
      input: prompt,
      max_tokens: maxTokens,
      temperature,
    });

    const text = response.output?.[0]?.content || '';
    const tokensUsed = response.usage?.total_tokens || 0;
    const costUsd = calculateCost(tokensUsed, model);

    // Log operation
    await logAIOperation({
      operationId,
      type: 'chat',
      model,
      prompt,
      response: text,
      tokensUsed,
      costUsd,
    });

    return {
      text,
      tokensUsed,
      costUsd,
      model,
    };
  }, 'chat');

  return result;
}
