/**
 * Trust Compliance Module — Core Type Definitions
 *
 * Defines all shared types for the Trust Document Compliance Refactor
 * agent swarm: intake, classification, rewrite, evidence binder,
 * recommendation, receipt, and orchestrator.
 */

// ── Risk Tags ────────────────────────────────────────────────────────────────

export type RiskTag =
  | 'TRUST_ADMIN'
  | 'BANKING_AUTHORITY'
  | 'UCC_RECORD'
  | 'TAX_POSITION'
  | 'A4V_LANGUAGE'
  | 'NONRESIDENT_CLAIM'
  | 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM'
  | 'SELF_EXECUTING_CONTRACT'
  | 'MARITIME_LIEN_CLAIM'
  | 'THREATENING_FEE_SCHEDULE'
  | 'REWRITE_REQUIRED'
  | 'DO_NOT_SEND';

// ── Clause Classification ─────────────────────────────────────────────────────

/**
 * GREEN  = Usable with minor review.
 * YELLOW = Useful intent but rewrite required before external use.
 * RED    = Do not send/file/rely on without attorney or CPA review.
 */
export type ClauseClassification = 'GREEN' | 'YELLOW' | 'RED';

// ── Destination Context ───────────────────────────────────────────────────────

export type DestinationContext =
  | 'bank'
  | 'court'
  | 'irs_tax'
  | 'credit_bureau'
  | 'creditor'
  | 'internal_trust_record';

// ── Document Intake ───────────────────────────────────────────────────────────

export interface DocumentSection {
  id: string;
  title: string;
  content: string;
}

export interface ParsedDocument {
  id: string;
  title: string;
  date: string;
  parties: string[];
  addresses: string[];
  filingNumbers: string[];
  sensitiveDataFlags: string[];
  sections: DocumentSection[];
  documentType: string;
}

// ── Risk Classifier ───────────────────────────────────────────────────────────

export interface ClassifiedClause {
  sectionId: string;
  sectionTitle: string;
  content: string;
  classification: ClauseClassification;
  riskTags: RiskTag[];
  reason: string;
}

// ── Compliance Rewrite ────────────────────────────────────────────────────────

export interface RewrittenClause {
  original: ClassifiedClause;
  rewritten: string | null;
  blocked: boolean;
  blockReason?: string;
}

// ── Evidence Binder ───────────────────────────────────────────────────────────

export interface Exhibit {
  id: string;
  title: string;
  type: 'public' | 'reserve';
  description: string;
  source: string;
  restricted: boolean;
}

export interface ExhibitIndex {
  public: Exhibit[];
  reserve: Exhibit[];
}

// ── Action Recommendation ─────────────────────────────────────────────────────

export interface ActionRecommendation {
  context: DestinationContext;
  permitted: string[];
  blocked: string[];
  rewrites: string[];
}

// ── Risk Register ─────────────────────────────────────────────────────────────

export interface RiskRegisterEntry {
  clauseId: string;
  sectionTitle: string;
  classification: ClauseClassification;
  riskTags: RiskTag[];
  reason: string;
  action: 'use' | 'rewrite' | 'block';
}

// ── Run Receipt ───────────────────────────────────────────────────────────────

export interface RunReceiptAction {
  step: string;
  timestamp: string;
  detail: string;
}

export interface RunReceipt {
  runId: string;
  timestamp: string;
  documentId: string;
  documentTitle: string;
  totalClauses: number;
  greenCount: number;
  yellowCount: number;
  redCount: number;
  blockedExports: number;
  actions: RunReceiptAction[];
}

// ── Orchestrator Result ───────────────────────────────────────────────────────

export interface TrustComplianceMissionResult {
  document: ParsedDocument;
  riskRegister: RiskRegisterEntry[];
  exhibits: ExhibitIndex;
  recommendations: ActionRecommendation[];
  receipt: RunReceipt;
}
