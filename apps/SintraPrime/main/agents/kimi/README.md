# Kimi AI (Moonshot AI) Integration

This directory contains the integration for Kimi K 2.5, an advanced language model from Moonshot AI (moonshot.ai), into the SintraPrime agent framework.

## Overview

The Kimi agent provides:
- Chat completion API interface
- Streaming response support
- Automatic retry logic with exponential backoff
- Rate limiting compliance
- Error handling and logging

## Setup Instructions

### 1. API Key Configuration

Obtain a Kimi API key from [Moonshot AI](https://moonshot.ai) and configure it in your environment.

### 2. Environment Variables

Add the following to your `.env` file:

```bash
# Kimi AI (Moonshot AI) Configuration
KIMI_API_KEY=your_moonshot_api_key_here
KIMI_API_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-32k
KIMI_MAX_TOKENS=4000
KIMI_TEMPERATURE=0.7
```

### 3. Configuration File

A default configuration is available in `config/kimi-config.json`:

```json
{
  "provider": "moonshot",
  "model": "moonshot-v1-32k",
  "api_version": "v1",
  "default_params": {
    "temperature": 0.7,
    "max_tokens": 4000,
    "top_p": 1.0
  },
  "rate_limits": {
    "requests_per_minute": 60,
    "tokens_per_minute": 100000
  }
}
```

## Usage Examples

### Basic Chat Completion

```typescript
import { KimiAgent } from './agents/kimi/index.js';

const agent = new KimiAgent({
  apiKey: process.env.KIMI_API_KEY!,
  baseUrl: process.env.KIMI_API_BASE_URL || 'https://api.moonshot.cn/v1',
  model: process.env.KIMI_MODEL || 'moonshot-v1-32k',
  maxTokens: 4000,
  temperature: 0.7,
});

const messages = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Hello, how are you?' }
];

const response = await agent.chatCompletion(messages);
console.log(response.choices[0].message.content);
```

### Streaming Response

```typescript
const messages = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Tell me a story.' }
];

for await (const chunk of agent.streamChatCompletion(messages)) {
  const content = chunk.choices[0]?.delta?.content;
  if (content) {
    process.stdout.write(content);
  }
}
```

### Custom Parameters

```typescript
const response = await agent.chatCompletion(messages, {
  temperature: 0.9,
  maxTokens: 2000,
  topP: 0.95
});
```

## Integration Points

### DeepThink Operations

The Kimi agent can be integrated into DeepThink operations as an alternative reasoning engine:

```typescript
// In deepthink/src/deepthink.mjs or similar
import { KimiAgent } from '../../agents/kimi/index.js';

const kimiAgent = new KimiAgent({
  apiKey: process.env.KIMI_API_KEY!,
  baseUrl: process.env.KIMI_API_BASE_URL!,
  model: process.env.KIMI_MODEL!,
  maxTokens: parseInt(process.env.KIMI_MAX_TOKENS || '4000'),
  temperature: parseFloat(process.env.KIMI_TEMPERATURE || '0.7'),
});

// Use for analysis tasks
const analysis = await kimiAgent.chatCompletion([
  { role: 'system', content: 'You are an expert analyst.' },
  { role: 'user', content: analysisRequest }
]);
```

### Automation Scripts

Use Kimi in automation workflows:

```typescript
// In scripts/automation-with-kimi.ts
import { KimiAgent } from '../agents/kimi/index.js';

const agent = new KimiAgent({
  apiKey: process.env.KIMI_API_KEY!,
  baseUrl: process.env.KIMI_API_BASE_URL!,
  model: process.env.KIMI_MODEL!,
  maxTokens: 4000,
  temperature: 0.7,
});

// Automate content generation, analysis, etc.
```

### Agent Orchestration

Integrate with the agent registry for orchestrated workflows:

```typescript
// Register Kimi agent in agents/registry.json
{
  "name": "kimi-agent",
  "version": "1.0.0",
  "capabilities": ["chat.completion", "reasoning.alternative"]
}
```

## API Reference

### KimiAgent Class

#### Constructor

```typescript
constructor(config: KimiConfig)
```

**Parameters:**
- `config.apiKey`: Your Moonshot AI API key
- `config.baseUrl`: API base URL (default: `https://api.moonshot.cn/v1`)
- `config.model`: Model identifier (default: `moonshot-v1-32k`)
- `config.maxTokens`: Maximum tokens in response
- `config.temperature`: Sampling temperature (0-2)
- `config.topP`: Nucleus sampling parameter (optional)

#### Methods

##### `chatCompletion(messages, options?)`

Send a chat completion request.

**Parameters:**
- `messages`: Array of `KimiMessage` objects
- `options`: Optional parameters (temperature, maxTokens, topP)

**Returns:** `Promise<KimiResponse>`

##### `streamChatCompletion(messages, options?)`

Stream a chat completion response.

**Parameters:**
- `messages`: Array of `KimiMessage` objects
- `options`: Optional parameters (temperature, maxTokens, topP)

**Returns:** `AsyncGenerator<KimiStreamChunk>`

##### `getConfig()`

Get the current configuration.

**Returns:** `Readonly<KimiConfig>`

##### `getStats()`

Get request statistics.

**Returns:** `{ requestCount: number; lastRequestTime: number }`

## Error Handling

The agent implements comprehensive error handling:

1. **Validation Errors**: Thrown during initialization if required config is missing
2. **Network Errors**: Automatic retry with exponential backoff (up to 3 attempts)
3. **Rate Limit Errors (429)**: Automatic retry with backoff
4. **Server Errors (5xx)**: Automatic retry with backoff
5. **Client Errors (4xx)**: Immediate failure with detailed error message

## Rate Limiting

The agent includes basic rate limiting to comply with Moonshot AI's limits:

- **Requests per minute**: 60 (configurable in `config/kimi-config.json`)
- **Tokens per minute**: 100,000 (enforced by API)
- **Minimum delay between requests**: 1 second

For production use, consider implementing a more sophisticated rate limiting queue.

## Security Considerations

### API Key Security

- ✅ **Always use environment variables** for API keys
- ✅ **Never commit API keys** to version control
- ✅ **Rotate keys regularly** (recommended: every 90 days)
- ✅ **Use different keys** for development and production

### Network Security

- Requests use HTTPS only
- No sensitive data is logged
- Errors are sanitized before logging

### Governance Compliance

This integration follows SintraPrime's governance patterns:

1. **Isolation**: Runs in separate process context
2. **Least Privilege**: Uses minimal required permissions
3. **Consent**: All actions are logged and auditable

## Troubleshooting

### Common Issues

#### "API key is required" error

**Solution**: Ensure `KIMI_API_KEY` is set in your environment:

```bash
export KIMI_API_KEY=your_key_here
```

#### "Rate limit exceeded" error

**Solution**: The agent will automatically retry. If persistent, reduce request frequency or upgrade your API plan.

#### "Model not found" error

**Solution**: Verify the model name in your configuration:

```bash
KIMI_MODEL=moonshot-v1-32k
```

Available models:
- `moonshot-v1-32k` (32K context window)
- `moonshot-v1-8k` (8K context window)
- `moonshot-v1-128k` (128K context window)

#### Connection timeout

**Solution**: Check your network connection and ensure `api.moonshot.cn` is accessible.

## Testing

Run the test suite:

```bash
npm test tests/kimi/kimiAgent.test.ts
```

Tests include:
- Configuration validation
- Mock API response handling
- Error handling
- Retry logic
- Rate limiting

## Monitoring and Logging

The Kimi agent integrates with SintraPrime's monitoring system:

- All requests are logged to the audit trail
- Response times are tracked
- Error rates are monitored
- Token usage is recorded

## Version History

### v1.0.0 (2026-02-03)

- Initial implementation
- Chat completion support
- Streaming response support
- Retry logic with exponential backoff
- Basic rate limiting
- Comprehensive error handling

## Additional Resources

- [Moonshot AI Official Website](https://moonshot.ai)
- [Moonshot AI API Documentation](https://api.moonshot.cn/docs)
- [SintraPrime Governance Documentation](../../docs/governance/index.md)
- [Agent Registry](../registry.json)

## Support

For issues specific to:
- **Kimi agent**: Open an issue in this repository
- **Moonshot AI API**: Contact Moonshot AI support
- **SintraPrime governance**: Review policy documents in `/docs/governance/`

---

**Version:** 1.0.0  
**Date:** 2026-02-03  
**Status:** Production Ready  
**Governance Compliance:** Follows SintraPrime isolation, least privilege, and consent patterns
