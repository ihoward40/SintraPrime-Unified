/**
 * OpenAI Client for SintraPrime
 * 
 * Provides AI-powered analysis and report generation for governance operations
 */

// Stub OpenAI type for when package is not installed
type OpenAIClient = any;

// OpenAI client instance (requires 'openai' package to be installed)
export const openai: OpenAIClient = null;

export function isAIAvailable(): boolean {
  return !!process.env.OPENAI_API_KEY && openai !== null;
}

/**
 * Generate analysis report with AI
 */
export async function generateAnalysisReport(
  analysisData: any,
  options: { format?: 'markdown' | 'text' } = {}
): Promise<string> {
  if (!isAIAvailable()) {
    throw new Error('OpenAI client is not available. Set OPENAI_API_KEY environment variable and install the openai package.');
  }

  const { format = 'markdown' } = options;

  const prompt = `Generate a comprehensive governance analysis report based on the following data:

${JSON.stringify(analysisData, null, 2)}

Format the report as ${format} with the following sections:
1. Executive Summary
2. Key Findings
3. Risk Assessment
4. Recommendations
5. Compliance Status
6. Next Steps

Be professional, concise, and actionable.`;

  const response = await openai.responses.create({
    model: 'gpt-5',
    input: prompt,
    instructions: 'You are a governance and compliance analyst generating audit reports.',
  });

  return response.output?.[0]?.content || '';
}

/**
 * Generate natural language summary of DeepThink output
 */
export async function summarizeDeepThinkOutput(output: any): Promise<string> {
  if (!isAIAvailable()) {
    throw new Error('OpenAI client is not available. Set OPENAI_API_KEY environment variable and install the openai package.');
  }

  const prompt = `Summarize the following analysis output in clear, non-technical language:

${JSON.stringify(output, null, 2)}

Provide:
1. What was analyzed
2. Key findings (3-5 bullet points)
3. Overall assessment
4. Recommended actions

Keep it concise and suitable for executive review.`;

  const response = await openai.responses.create({
    model: 'gpt-5',
    input: prompt,
    temperature: 0.7,
  });

  return response.output?.[0]?.content || '';
}

/**
 * Generate visual diagram description for system architecture
 */
export async function generateDiagramDescription(
  systemComponents: string[]
): Promise<string> {
  const prompt = `Create a detailed description for a system architecture diagram with these components:

${systemComponents.join('\n')}

Describe:
1. Component relationships
2. Data flow
3. Security boundaries
4. Integration points

Format as a structured description suitable for diagram generation.`;

  const response = await openai.responses.create({
    model: 'gpt-5',
    input: prompt,
  });

  return response.output?.[0]?.content || '';
}
