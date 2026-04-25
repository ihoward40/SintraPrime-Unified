/**
 * Type definitions for Kimi AI (Moonshot AI) integration
 */

export interface KimiConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
  maxTokens: number;
  temperature: number;
  topP?: number;
}

export interface KimiMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface KimiRequestParams {
  model: string;
  messages: KimiMessage[];
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  stream?: boolean;
}

export interface KimiChoice {
  index: number;
  message: KimiMessage;
  finish_reason: string;
}

export interface KimiUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface KimiResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: KimiChoice[];
  usage: KimiUsage;
}

export interface KimiStreamChunk {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    delta: {
      role?: string;
      content?: string;
    };
    finish_reason: string | null;
  }>;
}

export interface KimiError {
  error: {
    message: string;
    type: string;
    code?: string;
  };
}

export interface KimiRateLimits {
  requestsPerMinute: number;
  tokensPerMinute: number;
}
