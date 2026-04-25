/**
 * Image Generation Service
 * 
 * Handles image generation using OpenAI DALL-E and GPT Image models
 */

import { v4 as uuidv4 } from 'uuid';
import { openai, calculateCost, logAIOperation, withOpenAIErrorHandling } from '../client';
import * as fs from 'fs/promises';
import * as path from 'path';

export interface ImageGenerationOptions {
  model?: 'dall-e-3' | 'gpt-image-1.5' | 'gpt-image-1';
  size?: '1024x1024' | '1792x1024' | '1024x1792';
  quality?: 'standard' | 'hd';
  style?: 'vivid' | 'natural';
  outputPath?: string;
}

export interface ImageGenerationResult {
  imageUrl?: string;
  imageData?: Buffer;
  revisedPrompt?: string;
  costUsd: number;
  model: string;
  localPath?: string;
}

/**
 * Generate image using DALL-E 3
 */
export async function generateImage(
  prompt: string,
  options: ImageGenerationOptions = {}
): Promise<ImageGenerationResult> {
  const {
    model = 'dall-e-3',
    size = '1024x1024',
    quality = 'standard',
    style = 'vivid',
    outputPath,
  } = options;

  const operationId = uuidv4();

  const result = await withOpenAIErrorHandling(async () => {
    const response = await openai.images.generate({
      model,
      prompt,
      size,
      quality,
      style,
      n: 1,
    });

    const imageUrl = response.data[0]?.url;
    const revisedPrompt = response.data[0]?.revised_prompt;
    const costUsd = calculateCost(1, model); // Per image cost

    let localPath: string | undefined;
    let imageData: Buffer | undefined;

    // Download image if URL provided
    if (imageUrl) {
      const imageResponse = await fetch(imageUrl);
      imageData = Buffer.from(await imageResponse.arrayBuffer());

      // Save to file if output path specified
      if (outputPath) {
        await fs.mkdir(path.dirname(outputPath), { recursive: true });
        await fs.writeFile(outputPath, imageData);
        localPath = outputPath;
      }
    }

    // Log operation
    await logAIOperation({
      operationId,
      type: 'image',
      model,
      prompt,
      response: { imageUrl, revisedPrompt, localPath },
      costUsd,
      metadata: { size, quality, style },
    });

    return {
      imageUrl,
      imageData,
      revisedPrompt,
      costUsd,
      model,
      localPath,
    };
  }, 'generateImage');

  return result;
}

/**
 * Generate image using GPT Image (via Responses API)
 */
export async function generateImageWithGPT(
  prompt: string,
  options: Omit<ImageGenerationOptions, 'model'> & { model?: 'gpt-image-1.5' | 'gpt-image-1' } = {}
): Promise<ImageGenerationResult> {
  const {
    model = 'gpt-image-1.5',
    outputPath,
  } = options;

  const operationId = uuidv4();

  const result = await withOpenAIErrorHandling(async () => {
    const response = await openai.responses.create({
      model: 'gpt-5', // GPT-5 with image generation tool
      input: `Generate an image: ${prompt}`,
      tools: [{ type: 'image_generation' }],
    });

    // Extract base64 image data from response
    const output = response.output?.[0];
    let imageData: Buffer | undefined;
    let localPath: string | undefined;

    if (output?.type === 'image' && output.image_data) {
      imageData = Buffer.from(output.image_data, 'base64');

      // Save to file if output path specified
      if (outputPath) {
        await fs.mkdir(path.dirname(outputPath), { recursive: true });
        await fs.writeFile(outputPath, imageData);
        localPath = outputPath;
      }
    }

    const tokensUsed = response.usage?.total_tokens || 0;
    const costUsd = calculateCost(tokensUsed, 'gpt-5');

    // Log operation
    await logAIOperation({
      operationId,
      type: 'image',
      model,
      prompt,
      response: { localPath },
      tokensUsed,
      costUsd,
    });

    return {
      imageData,
      costUsd,
      model,
      localPath,
    };
  }, 'generateImageWithGPT');

  return result;
}

/**
 * Generate multiple images with different prompts
 */
export async function generateMultipleImages(
  prompts: string[],
  options: ImageGenerationOptions = {}
): Promise<ImageGenerationResult[]> {
  const results: ImageGenerationResult[] = [];

  for (let i = 0; i < prompts.length; i++) {
    const prompt = prompts[i];
    const outputPath = options.outputPath
      ? options.outputPath.replace(/(\.[^.]+)$/, `_${i + 1}$1`)
      : undefined;

    const result = await generateImage(prompt, {
      ...options,
      outputPath,
    });

    results.push(result);
  }

  return results;
}

/**
 * Generate image for specific use case (letterhead, diagram, etc.)
 */
export async function generateDocumentAsset(
  assetType: 'letterhead' | 'logo' | 'diagram' | 'chart',
  description: string,
  options: ImageGenerationOptions = {}
): Promise<ImageGenerationResult> {
  const prompts: Record<string, string> = {
    letterhead: `Professional letterhead design: ${description}. Clean, modern, suitable for legal documents.`,
    logo: `Professional logo design: ${description}. Simple, memorable, scalable vector style.`,
    diagram: `Technical diagram: ${description}. Clear, well-labeled, professional style.`,
    chart: `Data visualization chart: ${description}. Clean, readable, professional business style.`,
  };

  const prompt = prompts[assetType] || description;

  return generateImage(prompt, {
    ...options,
    style: 'natural', // More professional for documents
    quality: 'hd', // Higher quality for print
  });
}
