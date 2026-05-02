/**
 * Trust Compliance Orchestrator
 *
 * Entry point for the Trust Document Compliance Refactor agent swarm.
 * Coordinates the six agents in sequence:
 *
 *   1. Document Intake Agent  — parse and segment the document
 *   2. Risk Classifier Agent  — classify each clause GREEN / YELLOW / RED
 *   3. Compliance Rewrite Agent — rewrite YELLOW; block RED
 *   4. Evidence Binder Agent  — build public / reserve exhibit index
 *   5. Action Recommendation Agent — per-context action recommendations
 *   6. Receipt Agent          — emit immutable run receipt
 *
 * Governance:
 *   - RED clauses are NEVER exported for external use.
 *   - YELLOW clauses require a compliance rewrite before external use.
 *   - All runs emit a receipt regardless of outcome.
 */

import { runIntakeAgent, type IntakeInput } from './intake.js';
import { runClassifierAgent } from './classifier.js';
import { runRewriteAgent } from './rewrite.js';
import { runEvidenceBinderAgent } from './evidence.js';
import { runRecommendationAgent } from './recommendation.js';
import { runReceiptAgent } from './receipt.js';
import type {
  TrustComplianceMissionResult,
  RiskRegisterEntry,
  ClassifiedClause,
} from '../types.js';

// ── Risk register builder ────────────────────────────────────────────────────

function buildRiskRegister(clauses: ClassifiedClause[]): RiskRegisterEntry[] {
  return clauses.map((clause, index) => ({
    clauseId: `clause_${index}_${clause.sectionId}`,
    sectionTitle: clause.sectionTitle,
    classification: clause.classification,
    riskTags: clause.riskTags,
    reason: clause.reason,
    action:
      clause.classification === 'RED'
        ? 'block'
        : clause.classification === 'YELLOW'
          ? 'rewrite'
          : 'use',
  }));
}

// ── Orchestrator ─────────────────────────────────────────────────────────────

/**
 * Run the full Trust Compliance Mission on raw document text.
 *
 * @param input - Raw document text and optional metadata.
 * @returns TrustComplianceMissionResult containing document, riskRegister,
 *          exhibits, recommendations, and receipt.
 */
export async function runTrustComplianceMission(
  input: IntakeInput,
): Promise<TrustComplianceMissionResult> {
  // Step 1: Document Intake
  const document = runIntakeAgent(input);

  // Step 2: Risk Classification
  const clauses = runClassifierAgent(document);

  // Step 3: Compliance Rewrite (YELLOW → rewrite, RED → block)
  const rewrites = runRewriteAgent(clauses);

  // Step 4: Evidence Binder
  const exhibits = runEvidenceBinderAgent(document, clauses);

  // Step 5: Action Recommendations
  const recommendations = runRecommendationAgent(clauses);

  // Step 6: Risk Register
  const riskRegister = buildRiskRegister(clauses);

  // Step 7: Run Receipt (always emitted)
  const receipt = runReceiptAgent(document, clauses, rewrites, exhibits, recommendations);

  return { document, riskRegister, exhibits, recommendations, receipt };
}
