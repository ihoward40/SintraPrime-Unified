/**
 * Safety Gates
 *
 * Pre-flight checks that must pass before generating any letter, filing,
 * complaint, tax form, or notice. Each gate corresponds to a compliance
 * question from the governance specification.
 *
 * If any gate fails, the export is marked BLOCKED or REWRITE_REQUIRED.
 */

import type { ClauseClassification, DestinationContext, RiskTag } from '../types.js';

export type SafetyOutcome = 'ALLOW' | 'BLOCKED' | 'REWRITE_REQUIRED';

export interface SafetyGateResult {
  outcome: SafetyOutcome;
  flags: string[];
  recommendations: string[];
}

/**
 * Destination contexts that are considered external and subject to the
 * strictest safety gates.
 */
const EXTERNAL_CONTEXTS: DestinationContext[] = [
  'bank',
  'court',
  'irs_tax',
  'credit_bureau',
  'creditor',
];

/**
 * Risk tags that always result in a BLOCKED outcome when the destination
 * is external.
 */
const ALWAYS_BLOCK_TAGS: RiskTag[] = [
  'A4V_LANGUAGE',
  'NONRESIDENT_CLAIM',
  'BIRTH_CERTIFICATE_ACCOUNT_CLAIM',
  'THREATENING_FEE_SCHEDULE',
  'DO_NOT_SEND',
];

/**
 * Risk tags that require a REWRITE_REQUIRED outcome (not a full block)
 * when the destination is external.
 */
const REWRITE_TAGS: RiskTag[] = [
  'SELF_EXECUTING_CONTRACT',
  'MARITIME_LIEN_CLAIM',
  'REWRITE_REQUIRED',
];

/**
 * Run all safety gates for a clause before allowing export.
 *
 * @param classification - The clause's GREEN/YELLOW/RED classification.
 * @param riskTags - Risk tags applied to the clause.
 * @param destination - Target context for the output.
 * @returns SafetyGateResult with outcome and detailed flags.
 */
export function runSafetyGates(
  classification: ClauseClassification,
  riskTags: RiskTag[],
  destination: DestinationContext,
): SafetyGateResult {
  const flags: string[] = [];
  const recommendations: string[] = [];
  const isExternal = EXTERNAL_CONTEXTS.includes(destination);

  // Gate 1: RED clauses are never exported externally
  if (classification === 'RED' && isExternal) {
    flags.push('RED clause cannot be exported to external destination.');
    recommendations.push('Obtain attorney/CPA review before any external use.');
    return { outcome: 'BLOCKED', flags, recommendations };
  }

  // Gate 2: Always-block tags in external contexts
  const blockingTags = riskTags.filter((t) => ALWAYS_BLOCK_TAGS.includes(t));
  if (blockingTags.length > 0 && isExternal) {
    flags.push(`Blocking risk tag(s) detected: ${blockingTags.join(', ')}.`);
    recommendations.push('Remove or replace this language before any external submission.');
    return { outcome: 'BLOCKED', flags, recommendations };
  }

  // Gate 3: Tax-sensitive content requires professional sign-off notice
  if (riskTags.includes('TAX_POSITION') && (destination === 'irs_tax' || destination === 'bank')) {
    flags.push('TAX_POSITION tag detected for tax/banking destination.');
    recommendations.push('Require CPA or tax-attorney review before submission.');
  }

  // Gate 4: YELLOW clauses require rewrite before external use
  if (classification === 'YELLOW' && isExternal) {
    const rewriteNeeded = riskTags.filter((t) => REWRITE_TAGS.includes(t));
    flags.push('YELLOW clause requires compliance rewrite before external use.');
    if (rewriteNeeded.length > 0) {
      flags.push(`Rewrite-required tag(s): ${rewriteNeeded.join(', ')}.`);
    }
    recommendations.push('Apply Compliance Rewrite Agent before exporting this clause.');
    return { outcome: 'REWRITE_REQUIRED', flags, recommendations };
  }

  // Gate 5: Banking authority claims need verification
  if (riskTags.includes('BANKING_AUTHORITY') && destination === 'bank') {
    flags.push('BANKING_AUTHORITY tag: verify authority with the institution before submission.');
    recommendations.push('Confirm trustee signing authority with the bank compliance team.');
  }

  // All gates passed
  return { outcome: 'ALLOW', flags, recommendations };
}
