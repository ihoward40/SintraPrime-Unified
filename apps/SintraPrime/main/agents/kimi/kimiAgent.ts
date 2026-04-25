/**
 * Kimi Agent - Integration with Moonshot AI's Kimi K 2.5
 * 
 * This agent provides interface to Moonshot AI's language model for chat completions
 * and streaming responses, following SintraPrime's governance patterns.
 */

/// <reference lib="dom" />

import type {
  KimiConfig,
  KimiMessage,
  KimiRequestParams,
  KimiResponse,
  KimiStreamChunk,
  KimiError,
} from './types.js';

export class KimiAgent {
  private config: KimiConfig;
  private requestCount: number = 0;
  private lastRequestTime: number = 0;

  constructor(config: KimiConfig) {
    this.config = config;
    this.validateConfig();
  }

  private validateConfig(): void {
    if (!this.config.apiKey) {
      throw new Error('Kimi API key is required');
    }
    if (!this.config.baseUrl) {
      throw new Error('Kimi base URL is required');
    }
    if (!this.config.model) {
      throw new Error('Kimi model is required');
    }
  }

  /**
   * Send a chat completion request to Kimi AI
   */
  async chatCompletion(
    messages: KimiMessage[],
    options?: {
      temperature?: number;
      maxTokens?: number;
      topP?: number;
    }
  ): Promise<KimiResponse> {
    this.enforceRateLimit();

    const requestBody: KimiRequestParams = {
      model: this.config.model,
      messages,
      temperature: options?.temperature ?? this.config.temperature,
      max_tokens: options?.maxTokens ?? this.config.maxTokens,
      top_p: options?.topP ?? this.config.topP,
      stream: false,
    };

    try {
      const response = await this.makeRequest('/chat/completions', requestBody);
      return response as KimiResponse;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Stream a chat completion response from Kimi AI
   */
  async *streamChatCompletion(
    messages: KimiMessage[],
    options?: {
      temperature?: number;
      maxTokens?: number;
      topP?: number;
    }
  ): AsyncGenerator<KimiStreamChunk, void, unknown> {
    this.enforceRateLimit();

    const requestBody: KimiRequestParams = {
      model: this.config.model,
      messages,
      temperature: options?.temperature ?? this.config.temperature,
      max_tokens: options?.maxTokens ?? this.config.maxTokens,
      top_p: options?.topP ?? this.config.topP,
      stream: true,
    };

    try {
      const response = await fetch(
        `${this.config.baseUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config.apiKey}`,
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        const errorData = await response.json() as KimiError;
        throw new Error(
          `Kimi API error: ${errorData.error?.message || response.statusText}`
        );
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed === '' || trimmed === 'data: [DONE]') continue;
          if (trimmed.startsWith('data: ')) {
            try {
              const chunk = JSON.parse(trimmed.substring(6)) as KimiStreamChunk;
              yield chunk;
            } catch (e) {
              console.error('Error parsing stream chunk:', e);
            }
          }
        }
      }
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Make an HTTP request to the Kimi API with retry logic
   */
  private async makeRequest(
    endpoint: string,
    body: unknown,
    retries: number = 3
  ): Promise<unknown> {
    const url = `${this.config.baseUrl}${endpoint}`;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config.apiKey}`,
          },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          const errorData = await response.json() as KimiError;
          
          // Retry on rate limit or server errors
          if (
            response.status === 429 ||
            (response.status >= 500 && attempt < retries)
          ) {
            await this.delay(Math.pow(2, attempt) * 1000);
            continue;
          }

          throw new Error(
            `Kimi API error (${response.status}): ${
              errorData.error?.message || response.statusText
            }`
          );
        }

        return await response.json();
      } catch (error) {
        if (attempt === retries) {
          throw error;
        }
        // Retry on network errors
        await this.delay(Math.pow(2, attempt) * 1000);
      }
    }

    throw new Error('Max retries exceeded');
  }

  /**
   * Enforce rate limiting based on requests per minute
   */
  private enforceRateLimit(): void {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;

    // Simple rate limiting: ensure minimum delay between requests
    const minDelay = 1000; // 1 second between requests (60 requests/minute)
    if (timeSinceLastRequest < minDelay) {
      const delay = minDelay - timeSinceLastRequest;
      // This is synchronous delay which blocks - in production, use a proper queue
      const start = Date.now();
      while (Date.now() - start < delay) {
        // Busy wait
      }
    }

    this.lastRequestTime = Date.now();
    this.requestCount++;
  }

  /**
   * Delay execution for a specified number of milliseconds
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Handle and format errors from the API
   */
  private handleError(error: unknown): Error {
    if (error instanceof Error) {
      return error;
    }
    return new Error(`Unknown error: ${String(error)}`);
  }

  /**
   * Get current configuration
   */
  getConfig(): Readonly<KimiConfig> {
    return { ...this.config };
  }

  /**
   * Get request statistics
   */
  getStats(): { requestCount: number; lastRequestTime: number } {
    return {
      requestCount: this.requestCount,
      lastRequestTime: this.lastRequestTime,
    };
  }
}
