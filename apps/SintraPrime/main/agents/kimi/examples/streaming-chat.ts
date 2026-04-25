/**
 * Example of using the Kimi agent with streaming responses
 * 
 * Usage:
 *   KIMI_API_KEY=your_key npx tsx agents/kimi/examples/streaming-chat.ts
 */

import { KimiAgent } from '../index.js';

async function main() {
  // Check for API key
  const apiKey = process.env.KIMI_API_KEY;
  if (!apiKey) {
    console.error('Error: KIMI_API_KEY environment variable is required');
    console.error('Usage: KIMI_API_KEY=your_key npx tsx agents/kimi/examples/streaming-chat.ts');
    process.exit(1);
  }

  // Create agent instance
  const agent = new KimiAgent({
    apiKey,
    baseUrl: process.env.KIMI_API_BASE_URL || 'https://api.moonshot.cn/v1',
    model: process.env.KIMI_MODEL || 'moonshot-v1-32k',
    maxTokens: parseInt(process.env.KIMI_MAX_TOKENS || '4000'),
    temperature: parseFloat(process.env.KIMI_TEMPERATURE || '0.7'),
  });

  console.log('Kimi Agent - Streaming Example');
  console.log('================================');
  console.log();

  // Example: Stream a longer response
  console.log('User: Tell me a short story about a robot learning to code.');
  console.log('Assistant: ');

  try {
    for await (const chunk of agent.streamChatCompletion([
      { role: 'system', content: 'You are a creative storyteller.' },
      { role: 'user', content: 'Tell me a short story about a robot learning to code.' }
    ])) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        process.stdout.write(content);
      }
    }
    console.log();
    console.log();
    console.log('Stream completed successfully!');
  } catch (error) {
    console.error('\nError:', error);
  }

  // Show stats
  const stats = agent.getStats();
  console.log();
  console.log('Agent statistics:');
  console.log(`- Total requests: ${stats.requestCount}`);
}

main().catch(console.error);
