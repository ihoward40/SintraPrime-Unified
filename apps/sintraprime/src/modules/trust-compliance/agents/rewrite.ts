/**
 * Compliance Rewrite Agent
 *
 * Converts YELLOW-classified clauses into bank-safe, court-safe,
 * agency-safe language while preserving lawful intent.
 *
 * RED clauses are marked BLOCKED — they are never rewritten for external use.
 * GREEN clauses pass through unchanged.
 *
 * Safe framing preserved: trust law, contract law, fiduciary duty,
 * due process, accounting, verification, good faith, and administrative
 * fairness principles.
 */

import type { ClassifiedClause, RewrittenClause } from '../types.js';

// ── Rewrite rule engine ───────────────────────────────────────────────────────

interface RewriteRule {
  /** Pattern to detect in the original text (case-insensitive). */
  pattern: RegExp;
  /** Safe replacement string. */
  replacement: string;
}

const REWRITE_RULES: RewriteRule[] = [
  // Self-executing / deemed-accepted language
  {
    pattern: /by\s+(?:your\s+)?acceptance\s+of\s+this\s+(?:notice|document|agreement)/gi,
    replacement:
      'Upon written agreement of the parties to this instrument',
  },
  {
    pattern: /your\s+failure\s+to\s+respond\s+(?:within\s+\d+\s+days?\s+)?(?:shall|will)\s+(?:constitute|be\s+deemed)/gi,
    replacement:
      'Any dispute of this instrument should be raised in writing within a reasonable time',
  },
  {
    pattern: /(?:silence\s+is\s+consent|tacit\s+(?:consent|procuration|agreement))/gi,
    replacement:
      'Consent to the terms of this instrument must be expressed in writing',
  },
  {
    pattern: /deemed\s+accepted/gi,
    replacement: 'accepted upon mutual written agreement',
  },

  // Administrative remedy language
  {
    pattern: /administrative\s+remedy\s+exhausted/gi,
    replacement: 'good-faith administrative inquiry submitted',
  },
  {
    pattern: /notice\s+of\s+dishonor/gi,
    replacement: 'written objection to the transaction in question',
  },
  {
    pattern: /notice\s+of\s+default/gi,
    replacement: 'written notice of payment delinquency',
  },

  // Private / non-domestic framing
  {
    pattern: /\bprivate\b(?=\s+(?:contract|agreement|bond|notice|offer))/gi,
    replacement: 'bilateral',
  },

  // Tax-position language — soften without removing substance
  {
    pattern: /exempt\s+from\s+withholding/gi,
    replacement: 'potentially exempt from withholding (subject to CPA verification)',
  },
  {
    pattern: /nonresident\s+alien/gi,
    replacement: 'foreign person (classification subject to IRS determination)',
  },

  // W-8 context softening
  {
    pattern: /\bw-?8\s*ben\b/gi,
    replacement: 'IRS Form W-8BEN (foreign status certification — verify eligibility with tax counsel)',
  },

  // Security agreement language
  {
    pattern: /self[\s-]executing\s+security\s+agreement/gi,
    replacement: 'security agreement subject to mutual execution and UCC filing',
  },
];

/**
 * Apply rewrite rules to clause content.
 */
function applyRewrites(content: string): string {
  let result = content;
  for (const rule of REWRITE_RULES) {
    result = result.replace(rule.pattern, rule.replacement);
  }
  return result;
}

/**
 * Run the Compliance Rewrite Agent on a classified clause.
 *
 * - GREEN → returned unchanged (blocked = false, rewritten = null).
 * - YELLOW → rewrite applied; blocked = false.
 * - RED → blocked = true; rewritten = null; no content produced.
 */
export function rewriteClause(clause: ClassifiedClause): RewrittenClause {
  if (clause.classification === 'RED') {
    return {
      original: clause,
      rewritten: null,
      blocked: true,
      blockReason:
        'RED-classified clause blocked from external use. ' +
        'Obtain attorney or CPA review before any use of this language.',
    };
  }

  if (clause.classification === 'GREEN') {
    return {
      original: clause,
      rewritten: null,
      blocked: false,
    };
  }

  // YELLOW: apply rewrites
  const rewritten = applyRewrites(clause.content);
  return {
    original: clause,
    rewritten,
    blocked: false,
  };
}

/**
 * Run the Compliance Rewrite Agent on all classified clauses.
 */
export function runRewriteAgent(clauses: ClassifiedClause[]): RewrittenClause[] {
  return clauses.map(rewriteClause);
}
