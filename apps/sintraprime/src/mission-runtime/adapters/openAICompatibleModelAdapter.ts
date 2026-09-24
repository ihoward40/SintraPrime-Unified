import type { MissionSpec, MissionState, ModelAdapter, ModelProposal } from '../types.js';

export interface OpenAICompatibleModelAdapterConfig {
  id: string;
  baseUrl: string;
  model: string;
  apiKeyEnv?: string;
  timeoutMs?: number;
}

export class OpenAICompatibleModelAdapter implements ModelAdapter {
  readonly id: string;
  private readonly config: OpenAICompatibleModelAdapterConfig;

  constructor(config: OpenAICompatibleModelAdapterConfig) {
    this.id = config.id;
    this.config = config;
  }

  async propose(spec: MissionSpec, state: MissionState, context?: unknown): Promise<ModelProposal> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.timeoutMs ?? 60_000);
    const apiKey = this.config.apiKeyEnv ? process.env[this.config.apiKeyEnv] : undefined;

    const system = [
      'You are a proposal engine inside SintraPrime.',
      'You do not have execution authority.',
      'Return exactly one JSON object and no markdown.',
      'Either propose one action or set stop=true.',
      'Never claim an action occurred.',
      'The runtime independently enforces model, tool, budget, and principal authority.',
    ].join(' ');

    const payload = {
      model: this.config.model,
      temperature: 0.2,
      messages: [
        { role: 'system', content: system },
        {
          role: 'user',
          content: JSON.stringify({ mission: spec, state, context }),
        },
      ],
      response_format: { type: 'json_object' },
    };

    try {
      const response = await fetch(`${this.config.baseUrl.replace(/\/$/, '')}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(apiKey ? { authorization: `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Model ${this.id} failed with HTTP ${response.status}`);
      }

      const body = (await response.json()) as any;
      const raw = body?.choices?.[0]?.message?.content;
      if (typeof raw !== 'string') throw new Error(`Model ${this.id} returned no message content`);

      const parsed = JSON.parse(raw) as ModelProposal;
      return { ...parsed, modelId: this.id };
    } finally {
      clearTimeout(timeout);
    }
  }
}
