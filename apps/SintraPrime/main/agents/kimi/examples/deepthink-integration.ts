/**
 * Example of integrating Kimi agent with DeepThink operations
 * 
 * This demonstrates how Kimi can be used as an alternative reasoning engine
 * for analysis tasks within the SintraPrime framework.
 * 
 * Usage:
 *   KIMI_API_KEY=your_key npx tsx agents/kimi/examples/deepthink-integration.ts
 */

import { KimiAgent } from '../index.js';
import type { KimiMessage } from '../types.js';

/**
 * Simulate a DeepThink analysis request using Kimi as the reasoning engine
 */
async function performDeepThinkAnalysis(
  agent: KimiAgent,
  analysisType: string,
  context: string
): Promise<string> {
  const systemPrompt = `You are an expert analyst working within the SintraPrime framework.
Your role is to provide thorough, well-reasoned analysis for ${analysisType}.
Focus on accuracy, clarity, and actionable insights.`;

  const userPrompt = `Perform a ${analysisType} analysis on the following:

${context}

Provide a structured analysis with:
1. Summary
2. Key findings
3. Recommendations
4. Potential risks or considerations`;

  const messages: KimiMessage[] = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt }
  ];

  const response = await agent.chatCompletion(messages, {
    temperature: 0.3, // Lower temperature for more focused analysis
    maxTokens: 2000,
  });

  return response.choices[0].message.content;
}

async function main() {
  // Check for API key
  const apiKey = process.env.KIMI_API_KEY;
  if (!apiKey) {
    console.error('Error: KIMI_API_KEY environment variable is required');
    console.error('Usage: KIMI_API_KEY=your_key npx tsx agents/kimi/examples/deepthink-integration.ts');
    process.exit(1);
  }

  // Initialize Kimi agent with DeepThink-optimized settings
  const agent = new KimiAgent({
    apiKey,
    baseUrl: process.env.KIMI_API_BASE_URL || 'https://api.moonshot.cn/v1',
    model: process.env.KIMI_MODEL || 'moonshot-v1-32k',
    maxTokens: 4000,
    temperature: 0.3, // Lower for analytical tasks
  });

  console.log('Kimi DeepThink Integration Example');
  console.log('===================================');
  console.log();

  // Example 1: Code review analysis
  console.log('Example 1: Code Review Analysis');
  console.log('--------------------------------');
  
  const codeReviewContext = `
Function: calculateUserScore(user)
- Takes user object as input
- Performs multiple database queries inside a loop
- No error handling for null values
- Returns score or -1 on error
`;

  try {
    const analysis = await performDeepThinkAnalysis(
      agent,
      'code review',
      codeReviewContext
    );
    console.log(analysis);
    console.log();
  } catch (error) {
    console.error('Error:', error);
  }

  // Example 2: Security analysis
  console.log('Example 2: Security Analysis');
  console.log('----------------------------');
  
  const securityContext = `
API Endpoint: /api/users/{userId}/profile
- Accepts userId from URL parameter
- Constructs SQL query using string concatenation
- No rate limiting
- Returns user profile data including email
`;

  try {
    const analysis = await performDeepThinkAnalysis(
      agent,
      'security',
      securityContext
    );
    console.log(analysis);
    console.log();
  } catch (error) {
    console.error('Error:', error);
  }

  // Show usage statistics
  const stats = agent.getStats();
  console.log('Analysis Statistics:');
  console.log(`- Total analyses performed: ${stats.requestCount}`);
  console.log(`- Last analysis time: ${new Date(stats.lastRequestTime).toISOString()}`);
  console.log();
  console.log('Note: These analyses would typically be stored in runs/ directory');
  console.log('with appropriate manifests and SHA-256 checksums per SintraPrime governance.');
}

main().catch(console.error);
