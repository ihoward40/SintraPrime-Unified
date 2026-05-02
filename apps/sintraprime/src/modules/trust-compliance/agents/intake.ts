/**
 * Document Intake Agent
 *
 * Reads uploaded document text, segments it into sections, and extracts
 * metadata: document ID, title, date, parties, addresses, filing numbers,
 * and sensitive-data flags.
 */

import { createHash } from 'node:crypto';
import type { ParsedDocument, DocumentSection } from '../types.js';

export interface IntakeInput {
  rawText: string;
  filename?: string;
  uploadedAt?: string;
}

/**
 * Patterns used to detect sensitive data in document text.
 */
const SENSITIVE_PATTERNS: Array<{ label: string; pattern: RegExp }> = [
  { label: 'SSN', pattern: /\b\d{3}-\d{2}-\d{4}\b/ },
  { label: 'EIN', pattern: /\b\d{2}-\d{7}\b/ },
  { label: 'AccountNumber', pattern: /\baccount\s*#?\s*\d{4,}\b/i },
  { label: 'RoutingNumber', pattern: /\brouting\s*#?\s*\d{9}\b/i },
];

/**
 * Infer a document type from its title or content.
 */
function inferDocumentType(title: string, content: string): string {
  const combined = `${title} ${content}`.toLowerCase();
  if (combined.includes('certification of trust') || combined.includes('certificate of trust')) {
    return 'CERTIFICATION_OF_TRUST';
  }
  if (combined.includes('ucc') && combined.includes('financing statement')) {
    return 'UCC_FINANCING_STATEMENT';
  }
  if (combined.includes('security agreement')) {
    return 'SECURITY_AGREEMENT';
  }
  if (combined.includes('affidavit')) {
    return 'AFFIDAVIT';
  }
  if (combined.includes('banking resolution') || combined.includes('bank resolution')) {
    return 'BANKING_RESOLUTION';
  }
  if (combined.includes('trustee minutes') || combined.includes('minutes of the trustee')) {
    return 'TRUSTEE_MINUTES';
  }
  if (combined.includes('w-8') || combined.includes('w8')) {
    return 'TAX_FORM_W8';
  }
  if (combined.includes('1099') || combined.includes('w-9') || combined.includes('w9')) {
    return 'TAX_FORM';
  }
  return 'GENERAL_TRUST_DOCUMENT';
}

/**
 * Split raw text into logical sections by common heading patterns.
 */
function splitIntoSections(text: string): DocumentSection[] {
  // Split on lines that look like section headings (all-caps, numbered, or
  // lines ending with a colon on their own).
  const lines = text.split('\n');
  const sections: DocumentSection[] = [];
  let currentTitle = 'Introduction';
  let currentLines: string[] = [];
  let sectionIndex = 0;

  const headingPattern = /^(\d+[\.\)]?\s+[A-Z]|[A-Z][A-Z\s]{4,}|#{1,3}\s+\S)/;

  for (const line of lines) {
    if (headingPattern.test(line.trim()) && currentLines.length > 0) {
      sections.push({
        id: `section_${sectionIndex++}`,
        title: currentTitle.trim(),
        content: currentLines.join('\n').trim(),
      });
      currentTitle = line.trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  // Push the final section
  if (currentLines.length > 0 || sections.length === 0) {
    sections.push({
      id: `section_${sectionIndex}`,
      title: currentTitle.trim(),
      content: currentLines.join('\n').trim(),
    });
  }

  return sections;
}

/**
 * Extract party names from text (simple heuristic: lines containing
 * "Trustee", "Grantor", "Beneficiary", "Party", or proper-noun pairs).
 */
function extractParties(text: string): string[] {
  const parties: string[] = [];
  const partyPattern =
    /(?:trustee|grantor|settlor|beneficiary|party|by and between)[:\s]+([A-Z][a-zA-Z\s,]+?)(?:\n|,|;|\.)/gi;
  let match: RegExpExecArray | null;
  while ((match = partyPattern.exec(text)) !== null) {
    const candidate = match[1]?.trim();
    if (candidate && candidate.length > 2 && !parties.includes(candidate)) {
      parties.push(candidate);
    }
  }
  return parties.slice(0, 10); // cap at 10
}

/**
 * Extract mailing addresses (US-style heuristic).
 */
function extractAddresses(text: string): string[] {
  const addresses: string[] = [];
  const addrPattern = /\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Drive|Dr|Lane|Ln|Way)\b[^,\n]*,\s*[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\s+\d{5}/g;
  let match: RegExpExecArray | null;
  while ((match = addrPattern.exec(text)) !== null) {
    const addr = match[0].trim();
    if (!addresses.includes(addr)) {
      addresses.push(addr);
    }
  }
  return addresses;
}

/**
 * Extract UCC / court filing numbers.
 */
function extractFilingNumbers(text: string): string[] {
  const numbers: string[] = [];
  const filingPattern = /(?:filing\s*(?:no|number|#)|document\s*(?:no|number|#)|ucc[\s-]?\d+)[:\s#]*([A-Z0-9\-]{5,20})/gi;
  let match: RegExpExecArray | null;
  while ((match = filingPattern.exec(text)) !== null) {
    const num = match[1]?.trim();
    if (num && !numbers.includes(num)) {
      numbers.push(num);
    }
  }
  return numbers;
}

/**
 * Detect sensitive data flags present in the text.
 */
function detectSensitiveFlags(text: string): string[] {
  return SENSITIVE_PATTERNS
    .filter(({ pattern }) => pattern.test(text))
    .map(({ label }) => label);
}

/**
 * Extract a date from the document text (first ISO or US-format date found).
 */
function extractDate(text: string): string {
  const isoMatch = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  if (isoMatch?.[1]) return isoMatch[1];
  const usMatch = text.match(/\b(\w+ \d{1,2},\s*\d{4})\b/);
  if (usMatch?.[1]) return usMatch[1];
  return new Date().toISOString().split('T')[0] ?? '';
}

/**
 * Extract a title from the first non-empty line of the document.
 */
function extractTitle(text: string, filename?: string): string {
  const firstLine = text.split('\n').find((l) => l.trim().length > 0);
  return firstLine?.trim() ?? filename ?? 'Untitled Document';
}

/**
 * Run the Document Intake Agent on raw document text.
 */
export function runIntakeAgent(input: IntakeInput): ParsedDocument {
  const { rawText, filename, uploadedAt } = input;
  const title = extractTitle(rawText, filename);
  const sections = splitIntoSections(rawText);
  const fullContent = rawText;

  const id = createHash('sha256')
    .update(`${title}:${uploadedAt ?? new Date().toISOString()}`)
    .digest('hex')
    .slice(0, 16);

  return {
    id,
    title,
    date: extractDate(fullContent),
    parties: extractParties(fullContent),
    addresses: extractAddresses(fullContent),
    filingNumbers: extractFilingNumbers(fullContent),
    sensitiveDataFlags: detectSensitiveFlags(fullContent),
    sections,
    documentType: inferDocumentType(title, fullContent),
  };
}
