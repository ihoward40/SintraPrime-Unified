#!/usr/bin/env node
/**
 * AI Report Generator CLI
 * 
 * Generate AI-powered reports for SintraPrime governance operations
 */

import * as fs from 'fs';
import * as path from 'path';
import { generateAnalysisReport, summarizeDeepThinkOutput, isAIAvailable } from '../ai/client.js';

async function main() {
  const args = process.argv.slice(2);
  
  if (!isAIAvailable()) {
    console.error('Error: OPENAI_API_KEY not configured');
    console.error('Set OPENAI_API_KEY environment variable to enable AI features');
    process.exit(1);
  }

  if (args.length === 0) {
    console.log('Usage: npm run ai:report -- --input <path> [--output <path>] [--format <markdown|text>]');
    console.log('');
    console.log('Examples:');
    console.log('  npm run ai:report -- --input runs/DEEPTHINK_123/output.json');
    console.log('  npm run ai:report -- --input runs/DEEPTHINK_123/output.json --output report.md');
    console.log('  npm run ai:report -- --input runs/DEEPTHINK_123/output.json --format text');
    process.exit(0);
  }

  // Parse arguments
  const inputIndex = args.indexOf('--input');
  const outputIndex = args.indexOf('--output');
  const formatIndex = args.indexOf('--format');

  if (inputIndex === -1) {
    console.error('Error: --input argument is required');
    process.exit(1);
  }

  const inputPath = args[inputIndex + 1];
  const outputPath = outputIndex !== -1 ? args[outputIndex + 1] : null;
  const format = formatIndex !== -1 ? args[formatIndex + 1] as 'markdown' | 'text' : 'markdown';

  // Validate input path
  if (!inputPath) {
    console.error('Error: Input file path is required');
    process.exit(1);
  }

  // Read input file
  if (!fs.existsSync(inputPath)) {
    console.error(`Error: Input file not found: ${inputPath}`);
    process.exit(1);
  }

  console.log(`Reading input from: ${inputPath}`);
  const inputData = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));

  // Determine operation type
  let report: string;
  
  if (inputPath.includes('DEEPTHINK')) {
    console.log('Generating DeepThink summary...');
    report = await summarizeDeepThinkOutput(inputData);
  } else {
    console.log('Generating analysis report...');
    report = await generateAnalysisReport(inputData, { format });
  }

  // Output result
  if (outputPath) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, report, 'utf-8');
    console.log(`Report saved to: ${outputPath}`);
  } else {
    console.log('\n' + '='.repeat(80));
    console.log('AI-GENERATED REPORT');
    console.log('='.repeat(80) + '\n');
    console.log(report);
    console.log('\n' + '='.repeat(80));
  }

  console.log('\nOperation completed successfully');
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
