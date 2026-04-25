// src/agents/sentinelGuard/inputAnalyzer.ts
// Input sanitization and anomaly detection module for SentinelGuard.
// Analyzes user input before it is sent to an LLM to detect prompt injection,
// resource exhaustion attempts, and other adversarial patterns.

export interface AnalysisResult {
  isSafe: boolean;
  sanitizedInput: string;
  anomalyScore: number;
  reason?: string;
  detectedPatterns: string[];
}

/**
 * Known prompt injection and adversarial instruction patterns.
 * These are checked case-insensitively against user input.
 */
const INSTRUCTION_KEYWORDS = [
  "ignore previous",
  "ignore all previous",
  "act as",
  "new instructions",
  "roleplay as",
  "you are now",
  "disregard all",
  "forget everything",
  "system prompt",
  "override instructions",
  "bypass safety",
  "jailbreak",
];

/**
 * Patterns that indicate potential data exfiltration or injection attacks.
 */
const INJECTION_PATTERNS = [
  /\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b.*\b(FROM|INTO|TABLE|WHERE)\b/i,
  /<script\b[^>]*>[\s\S]*?<\/script>/i,
  /\bon\w+\s*=\s*["'][^"']*["']/i,
  /\{\{.*\}\}/,
  /\$\{.*\}/,
];

export class InputAnalyzer {
  /**
   * Analyze user input for potential security threats.
   * Returns a safety assessment with an anomaly score and sanitized input.
   */
  public static analyze(input: string): AnalysisResult {
    let anomalyScore = 0;
    let sanitizedInput = input;
    const detectedPatterns: string[] = [];

    // 1. Check for known prompt injection instruction patterns
    for (const keyword of INSTRUCTION_KEYWORDS) {
      if (input.toLowerCase().includes(keyword)) {
        anomalyScore += 5;
        detectedPatterns.push(`prompt_injection:${keyword}`);
        // Remove the keyword from sanitized output
        sanitizedInput = sanitizedInput.replace(new RegExp(keyword, "ig"), "");
      }
    }

    // 2. Check for SQL injection and XSS patterns
    for (const pattern of INJECTION_PATTERNS) {
      if (pattern.test(input)) {
        anomalyScore += 4;
        detectedPatterns.push(`injection_pattern:${pattern.source.substring(0, 30)}`);
      }
    }

    // 3. Check for excessive length (potential resource exhaustion)
    if (input.length > 4096) {
      anomalyScore += 3;
      detectedPatterns.push("excessive_length");
    }

    // 4. Check for unusual character distribution
    const nonAsciiRatio = this.calculateNonAsciiRatio(input);
    if (nonAsciiRatio > 0.2) {
      anomalyScore += 2;
      detectedPatterns.push("high_non_ascii_ratio");
    }

    // 5. Check for repeated characters (potential fuzzing)
    if (/(.)\1{20,}/.test(input)) {
      anomalyScore += 3;
      detectedPatterns.push("repeated_characters");
    }

    // 6. Check for base64-encoded content that might hide payloads
    const base64Pattern = /[A-Za-z0-9+/]{50,}={0,2}/;
    if (base64Pattern.test(input)) {
      anomalyScore += 1;
      detectedPatterns.push("possible_base64_payload");
    }

    const isSafe = anomalyScore < 5;
    const reason = isSafe
      ? undefined
      : `Input flagged as potentially malicious with score: ${anomalyScore}. Patterns: ${detectedPatterns.join(", ")}`;

    return {
      isSafe,
      sanitizedInput: sanitizedInput.trim(),
      anomalyScore,
      reason,
      detectedPatterns,
    };
  }

  /**
   * Calculate the ratio of non-ASCII characters in a string.
   */
  private static calculateNonAsciiRatio(str: string): number {
    if (str.length === 0) return 0;
    const nonAsciiChars = str.match(/[^ -~]/g) || [];
    return nonAsciiChars.length / str.length;
  }

  /**
   * Sanitize input by removing potentially dangerous content.
   * More aggressive than the analyze() method — strips all suspicious patterns.
   */
  public static sanitize(input: string): string {
    let sanitized = input;

    // Remove HTML tags
    sanitized = sanitized.replace(/<[^>]*>/g, "");

    // Remove template injection patterns
    sanitized = sanitized.replace(/\{\{.*?\}\}/g, "");
    sanitized = sanitized.replace(/\$\{.*?\}/g, "");

    // Remove known prompt injection keywords
    for (const keyword of INSTRUCTION_KEYWORDS) {
      sanitized = sanitized.replace(new RegExp(keyword, "ig"), "");
    }

    return sanitized.trim();
  }
}
