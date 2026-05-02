/**
 * Receipt Agent
 *
 * Emits a run receipt for every intake, classification, rewrite, block,
 * export, and recommendation step executed by the Trust Compliance
 * Orchestrator.
 *
 * Receipts are immutable audit records and must never be modified after
 * emission.
 */

import { createHash } from 'node:crypto';
import type {
  ParsedDocument,
  ClassifiedClause,
  RewrittenClause,
  ExhibitIndex,
  ActionRecommendation,
  RunReceipt,
  RunReceiptAction,
} from '../types.js';

/**
 * Generate a deterministic run ID from document ID and timestamp.
 */
function generateRunId(documentId: string, timestamp: string): string {
  return createHash('sha256')
    .update(`${documentId}:${timestamp}`)
    .digest('hex')
    .slice(0, 24);
}

/**
 * Count exhibits across public and reserve lists.
 */
function countExhibits(exhibits: ExhibitIndex): number {
  return exhibits.public.length + exhibits.reserve.length;
}

/**
 * Build the ordered list of receipt action entries.
 */
function buildActions(
  document: ParsedDocument,
  clauses: ClassifiedClause[],
  rewrites: RewrittenClause[],
  exhibits: ExhibitIndex,
  recommendations: ActionRecommendation[],
  timestamp: string,
): RunReceiptAction[] {
  const actions: RunReceiptAction[] = [];

  actions.push({
    step: 'INTAKE',
    timestamp,
    detail: `Document "${document.title}" parsed. Type: ${document.documentType}. Sections: ${document.sections.length}.`,
  });

  actions.push({
    step: 'CLASSIFICATION',
    timestamp,
    detail:
      `Classified ${clauses.length} section(s). ` +
      `GREEN: ${clauses.filter((c) => c.classification === 'GREEN').length}, ` +
      `YELLOW: ${clauses.filter((c) => c.classification === 'YELLOW').length}, ` +
      `RED: ${clauses.filter((c) => c.classification === 'RED').length}.`,
  });

  const rewritten = rewrites.filter((r) => r.rewritten !== null);
  const blocked = rewrites.filter((r) => r.blocked);

  if (rewritten.length > 0) {
    actions.push({
      step: 'REWRITE',
      timestamp,
      detail: `${rewritten.length} clause(s) rewritten for compliance.`,
    });
  }

  if (blocked.length > 0) {
    actions.push({
      step: 'BLOCK',
      timestamp,
      detail: `${blocked.length} clause(s) blocked from external use (RED classification).`,
    });
  }

  actions.push({
    step: 'EXHIBIT_INDEX',
    timestamp,
    detail:
      `Evidence binder built. Public exhibits: ${exhibits.public.length}. ` +
      `Reserve exhibits: ${exhibits.reserve.length}.`,
  });

  actions.push({
    step: 'RECOMMENDATION',
    timestamp,
    detail: `Action recommendations generated for ${recommendations.length} destination context(s).`,
  });

  return actions;
}

/**
 * Run the Receipt Agent to produce an immutable run receipt.
 */
export function runReceiptAgent(
  document: ParsedDocument,
  clauses: ClassifiedClause[],
  rewrites: RewrittenClause[],
  exhibits: ExhibitIndex,
  recommendations: ActionRecommendation[],
): RunReceipt {
  const timestamp = new Date().toISOString();
  const runId = generateRunId(document.id, timestamp);

  const greenCount = clauses.filter((c) => c.classification === 'GREEN').length;
  const yellowCount = clauses.filter((c) => c.classification === 'YELLOW').length;
  const redCount = clauses.filter((c) => c.classification === 'RED').length;
  const blockedExports = rewrites.filter((r) => r.blocked).length;

  const actions = buildActions(document, clauses, rewrites, exhibits, recommendations, timestamp);

  return {
    runId,
    timestamp,
    documentId: document.id,
    documentTitle: document.title,
    totalClauses: clauses.length,
    greenCount,
    yellowCount,
    redCount,
    blockedExports,
    actions,
  };
}
