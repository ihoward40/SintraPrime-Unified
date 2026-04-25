/**
 * Basic example of using the Kimi agent for chat completion
 * 
 * Usage:
 *   KIMI_API_KEY=your_key npx tsx agents/kimi/examples/basic-chat.ts
 */

import { KimiAgent } from '../index.js';

async function main() {
  // Check for API key
  const apiKey = process.env.KIMI_API_KEY;
  if (!apiKey) {
    console.error('Error: KIMI_API_KEY environment variable is required');
    console.error('Usage: KIMI_API_KEY=your_key npx tsx agents/kimi/examples/basic-chat.ts');
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

  console.log('Kimi Agent initialized with config:');
  console.log(`- Model: ${agent.getConfig().model}`);
  console.log(`- Max Tokens: ${agent.getConfig().maxTokens}`);
  console.log(`- Temperature: ${agent.getConfig().temperature}`);
  console.log();

  // Example 1: Simple chat completion
  console.log('Example 1: Simple chat completion');
  console.log('=================================');
  
  try {
    const response = await agent.chatCompletion([
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'What is the capital of France?' }
    ]);

    console.log('User: What is the capital of France?');
    console.log(`Assistant: ${response.choices[0].message.content}`);
    console.log(`Tokens used: ${response.usage.total_tokens}`);
    console.log();
  } catch (error) {
    console.error('Error:', error);
  }

  // Example 2: Custom parameters
  console.log('Example 2: Chat with custom parameters');
  console.log('========================================');
  
  try {
    const response = await agent.chatCompletion(
      [
        { role: 'system', content: 'You are a creative writer.' },
        { role: 'user', content: 'Write a haiku about coding.' }
      ],
      {
        temperature: 0.9,
        maxTokens: 100,
      }
    );

    console.log('User: Write a haiku about coding.');
    console.log(`Assistant: ${response.choices[0].message.content}`);
    console.log(`Tokens used: ${response.usage.total_tokens}`);
    console.log();
  } catch (error) {
    console.error('Error:', error);
  }

  // Show stats
  const stats = agent.getStats();
  console.log('Agent statistics:');
  console.log(`- Total requests: ${stats.requestCount}`);
  console.log(`- Last request time: ${new Date(stats.lastRequestTime).toISOString()}`);
}

main().catch(console.error);
