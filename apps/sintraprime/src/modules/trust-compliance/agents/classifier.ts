/**
 * Risk Classifier Agent
 *
 * Performs clause-level classification for each section of a parsed document.
 *
 *   GREEN  — Usable with minor cleanup.
 *   YELLOW — Useful intent; rewrite required before external use.
 *   RED    — Do not send/file/rely on without attorney or CPA review.
 */

import type {
  ParsedDocument,
  DocumentSection,
  ClassifiedClause,
  ClauseClassification,
  RiskTag,
} from '../types.js';
import {
  findAllForbiddenPhrases,
} from '../policies/forbidden-phrases.js';

// ── Keyword maps ─────────────────────────────────────────────────────────────

/** Keywords that indicate trust-administration content (GREEN signal). */
const GREEN_KEYWORDS: string[] = [
  'certification of trust',
  'certificate of trust',
  'trustee authority',
  'fiduciary',
  'trust agreement',
  'trust instrument',
  'beneficiary',
  'successor trustee',
  'irrevocable trust',
  'revocable trust',
  'banking resolution',
  'trustee minutes',
  'ucc filing acknowledgment',
  'due process',
  'good faith',
  'administrative fairness',
  'verification',
  'accounting',
  'contract law',
];

/** Keywords that indicate moderate-risk / rewrite-required content (YELLOW signal). */
const YELLOW_KEYWORDS: string[] = [
  'self-executing',
  'self executing',
  'by acceptance',
  'your failure to respond',
  'deemed accepted',
  'tacit consent',
  'administrative remedy',
  'notice of dishonor',
  'notice of default',
  'security agreement',
  'w-8',
  'w8ben',
  'nonresident alien',
  'tax position',
  'exempt from withholding',
  'exempt organization',
  'private',
];

// ── Tag inference helpers ─────────────────────────────────────────────────────

function inferRiskTags(content: string, forbiddenReasons: string[]): RiskTag[] {
  const tags = new Set<RiskTag>();
  const lower = content.toLowerCase();

  // Derive tags from forbidden phrase reasons
  for (const reason of forbiddenReasons) {
    if (reason.includes('A4V_LANGUAGE')) tags.add('A4V_LANGUAGE');
    if (reason.includes('NONRESIDENT_CLAIM')) tags.add('NONRESIDENT_CLAIM');
    if (reason.includes('BIRTH_CERTIFICATE_ACCOUNT_CLAIM')) tags.add('BIRTH_CERTIFICATE_ACCOUNT_CLAIM');
    if (reason.includes('SELF_EXECUTING_CONTRACT')) tags.add('SELF_EXECUTING_CONTRACT');
    if (reason.includes('MARITIME_LIEN_CLAIM')) tags.add('MARITIME_LIEN_CLAIM');
    if (reason.includes('THREATENING_FEE_SCHEDULE')) tags.add('THREATENING_FEE_SCHEDULE');
  }

  // Content-based tag inference
  if (lower.includes('trust') || lower.includes('trustee') || lower.includes('fiduciary')) {
    tags.add('TRUST_ADMIN');
  }
  if (lower.includes('bank') || lower.includes('banking resolution') || lower.includes('financial institution')) {
    tags.add('BANKING_AUTHORITY');
  }
  if (lower.includes('ucc') || lower.includes('financing statement')) {
    tags.add('UCC_RECORD');
  }
  if (
    lower.includes('tax') ||
    lower.includes('irs') ||
    lower.includes('w-8') ||
    lower.includes('w-9') ||
    lower.includes('1099')
  ) {
    tags.add('TAX_POSITION');
  }
  if (lower.includes('security agreement')) {
    tags.add('SELF_EXECUTING_CONTRACT');
  }

  return Array.from(tags);
}

// ── Classification logic ──────────────────────────────────────────────────────

function classifySection(section: DocumentSection): ClassifiedClause {
  const content = section.content;
  const lower = content.toLowerCase();

  const forbidden = findAllForbiddenPhrases(content);
  const forbiddenReasons = forbidden.map((f) => f.reason);
  const riskTags = inferRiskTags(content, forbiddenReasons);

  // RED: any forbidden phrase present
  if (forbidden.length > 0) {
    const blockTags: RiskTag[] = ['DO_NOT_SEND', 'REWRITE_REQUIRED'];
    for (const tag of blockTags) {
      if (!riskTags.includes(tag)) riskTags.push(tag);
    }
    return {
      sectionId: section.id,
      sectionTitle: section.title,
      content: section.content,
      classification: 'RED' as ClauseClassification,
      riskTags,
      reason: `Forbidden phrase(s) detected: ${forbidden.map((f) => `"${f.phrase}"`).join(', ')}. ${forbiddenReasons[0] ?? ''}`,
    };
  }

  // YELLOW: moderate-risk keywords present
  const yellowMatch = YELLOW_KEYWORDS.find((kw) => lower.includes(kw));
  if (yellowMatch) {
    if (!riskTags.includes('REWRITE_REQUIRED')) riskTags.push('REWRITE_REQUIRED');
    return {
      sectionId: section.id,
      sectionTitle: section.title,
      content: section.content,
      classification: 'YELLOW' as ClauseClassification,
      riskTags,
      reason: `Moderate-risk keyword detected: "${yellowMatch}". Rewrite required before external use.`,
    };
  }

  // GREEN: trust-admin keywords or no risk signals
  const greenMatch = GREEN_KEYWORDS.find((kw) => lower.includes(kw));
  const reason = greenMatch
    ? `Trust-administration language detected ("${greenMatch}"). Usable with minor review.`
    : 'No risk signals detected. Usable with standard review.';

  return {
    sectionId: section.id,
    sectionTitle: section.title,
    content: section.content,
    classification: 'GREEN' as ClauseClassification,
    riskTags,
    reason,
  };
}

/**
 * Run the Risk Classifier Agent on a parsed document.
 * Returns one ClassifiedClause per document section.
 */
export function runClassifierAgent(document: ParsedDocument): ClassifiedClause[] {
  return document.sections.map(classifySection);
}
