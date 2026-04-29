/**
 * Action Recommendation Agent
 *
 * Produces per-destination-context action recommendations based on the
 * risk classification of a document's clauses.
 *
 * Destination contexts:
 *   bank            — Submission to a financial institution
 *   court           — Filing with a court
 *   irs_tax         — IRS or tax-authority submission
 *   credit_bureau   — Credit reporting agency dispute
 *   creditor        — Communication with a creditor
 *   internal_trust_record — Internal trust file only
 *
 * For each context the agent produces:
 *   permitted — Steps that are safe to proceed with.
 *   blocked   — Steps that must not proceed without further review.
 *   rewrites  — Steps that require rewrite before use.
 */

import type {
  ClassifiedClause,
  ActionRecommendation,
  DestinationContext,
  RiskTag,
} from '../types.js';

// ── Context definitions ───────────────────────────────────────────────────────

const ALL_CONTEXTS: DestinationContext[] = [
  'bank',
  'court',
  'irs_tax',
  'credit_bureau',
  'creditor',
  'internal_trust_record',
];

/**
 * Tags that block submission for a given destination context.
 */
const BLOCK_TAGS_BY_CONTEXT: Record<DestinationContext, RiskTag[]> = {
  bank: ['A4V_LANGUAGE', 'NONRESIDENT_CLAIM', 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM', 'THREATENING_FEE_SCHEDULE', 'DO_NOT_SEND'],
  court: ['A4V_LANGUAGE', 'NONRESIDENT_CLAIM', 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM', 'THREATENING_FEE_SCHEDULE', 'MARITIME_LIEN_CLAIM', 'DO_NOT_SEND'],
  irs_tax: ['A4V_LANGUAGE', 'NONRESIDENT_CLAIM', 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM', 'DO_NOT_SEND'],
  credit_bureau: ['A4V_LANGUAGE', 'THREATENING_FEE_SCHEDULE', 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM', 'DO_NOT_SEND'],
  creditor: ['A4V_LANGUAGE', 'THREATENING_FEE_SCHEDULE', 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM', 'DO_NOT_SEND'],
  internal_trust_record: [],
};

/**
 * Tags that require rewrite (not full block) for a given destination context.
 */
const REWRITE_TAGS_BY_CONTEXT: Record<DestinationContext, RiskTag[]> = {
  bank: ['SELF_EXECUTING_CONTRACT', 'REWRITE_REQUIRED', 'BANKING_AUTHORITY'],
  court: ['SELF_EXECUTING_CONTRACT', 'REWRITE_REQUIRED'],
  irs_tax: ['TAX_POSITION', 'SELF_EXECUTING_CONTRACT', 'REWRITE_REQUIRED'],
  credit_bureau: ['SELF_EXECUTING_CONTRACT', 'REWRITE_REQUIRED'],
  creditor: ['SELF_EXECUTING_CONTRACT', 'REWRITE_REQUIRED'],
  internal_trust_record: [],
};

// ── Permitted-step catalog ────────────────────────────────────────────────────

const PERMITTED_STEPS: Record<DestinationContext, string[]> = {
  bank: [
    'Submit Certification of Trust to establish trustee authority.',
    'Submit Banking Resolution authorizing account operations.',
    'Provide Trust EIN documentation.',
    'Submit Trustee identification and signature specimen.',
  ],
  court: [
    'File Certification of Trust as Exhibit.',
    'Submit UCC Filing Acknowledgment as supporting evidence.',
    'Include Trustee Minutes documenting relevant decisions.',
    'Attach notarized affidavit of facts in evidence.',
  ],
  irs_tax: [
    'Submit trust tax return (Form 1041) with CPA preparation.',
    'Provide EIN confirmation letter (IRS CP575).',
    'Respond to IRS notices via certified mail with signed correspondence.',
    'Provide corrected information returns as directed by CPA.',
  ],
  credit_bureau: [
    'Submit written dispute under FCRA § 623 or § 611.',
    'Attach supporting documentation (account statements, court orders, trust docs).',
    'Request investigation and method-of-verification disclosure.',
  ],
  creditor: [
    'Send validation-of-debt request under FDCPA § 809.',
    'Provide trust documentation establishing trustee authority.',
    'Negotiate repayment or settlement in writing.',
    'Document all communications for the trust file.',
  ],
  internal_trust_record: [
    'File all documents in the trust evidence binder.',
    'Cross-reference with risk register and exhibit index.',
    'Schedule annual trustee review.',
    'Archive original documents and compliance receipts.',
  ],
};

// ── Recommendation builder ────────────────────────────────────────────────────

function buildRecommendation(
  context: DestinationContext,
  clauses: ClassifiedClause[],
): ActionRecommendation {
  const blockTags = BLOCK_TAGS_BY_CONTEXT[context];
  const rewriteTags = REWRITE_TAGS_BY_CONTEXT[context];

  const blocked: string[] = [];
  const rewrites: string[] = [];

  for (const clause of clauses) {
    // Check for blocking tags
    const blocking = clause.riskTags.filter((t) => blockTags.includes(t));
    if (blocking.length > 0 || clause.classification === 'RED') {
      blocked.push(
        `Section "${clause.sectionTitle}": blocked for ${context} — ${blocking.join(', ') || 'RED classification'}.`,
      );
      continue;
    }

    // Check for rewrite-required tags
    const rewriteNeeded = clause.riskTags.filter((t) => rewriteTags.includes(t));
    if (rewriteNeeded.length > 0 || clause.classification === 'YELLOW') {
      rewrites.push(
        `Section "${clause.sectionTitle}": rewrite required for ${context} before use — ${rewriteNeeded.join(', ') || 'YELLOW classification'}.`,
      );
    }
  }

  // Only include permitted steps if no blocking issues for this context
  const hasBlockers = blocked.length > 0;
  const permitted = hasBlockers
    ? ['Resolve blocked clauses before proceeding with any submission.']
    : (PERMITTED_STEPS[context] ?? []);

  return { context, permitted, blocked, rewrites };
}

/**
 * Run the Action Recommendation Agent on all classified clauses.
 * Returns one recommendation per destination context.
 */
export function runRecommendationAgent(
  clauses: ClassifiedClause[],
): ActionRecommendation[] {
  return ALL_CONTEXTS.map((ctx) => buildRecommendation(ctx, clauses));
}
