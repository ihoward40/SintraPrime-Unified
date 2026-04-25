
/**
 * Monitoring types.
 *
 * This file supports both:
 * - The upstream snake_case monitoring model (RunRecord/CaseRecord)
 * - Legacy PascalCase monitoring model (RunRecordLegacy/CaseRecordLegacy)
 *
 * It also exports enum-like value objects (e.g. SeverityLevel.SEV0) alongside
 * string-literal union types, so code can use either style.
 */

export type Severity = 'SEV0' | 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4';
export const SeverityLevel = {
  SEV0: 'SEV0',
  SEV1: 'SEV1',
  SEV2: 'SEV2',
  SEV3: 'SEV3',
  SEV4: 'SEV4',
} as const;
export type SeverityLevel = Severity;

export type JobType =
  | 'ANALYSIS'
  | 'BINDER_EXPORT'
  | 'EMAIL_SEND'
  | 'RECONCILE_BACKFILL'
  | 'FILING'
  | 'OTHER';
export const JobType = {
  ANALYSIS: 'ANALYSIS',
  BINDER_EXPORT: 'BINDER_EXPORT',
  EMAIL_SEND: 'EMAIL_SEND',
  RECONCILE_BACKFILL: 'RECONCILE_BACKFILL',
  FILING: 'FILING',
  OTHER: 'OTHER',
} as const;

export type RunStatus = 'Success' | 'Failed' | 'Quarantined' | 'Escalated';
export const RunStatus = {
  Success: 'Success',
  Failed: 'Failed',
  Quarantined: 'Quarantined',
  Escalated: 'Escalated',
} as const;

export type MisconfigLikelihood = 'High' | 'Medium' | 'Low';
export const MisconfigLikelihood = {
  High: 'High',
  Medium: 'Medium',
  Low: 'Low',
} as const;

export type CaseCategory =
  | 'Cost/Credits'
  | 'Data/PII'
  | 'Delivery/Email'
  | 'Filing/Regulatory'
  | 'Reliability'
  | 'Other';
export const CaseCategory = {
  CostCredits: 'Cost/Credits',
  DataPII: 'Data/PII',
  DeliveryEmail: 'Delivery/Email',
  FilingRegulatory: 'Filing/Regulatory',
  Reliability: 'Reliability',
  Other: 'Other',
} as const;

export type CaseStatus = 'Open' | 'Investigating' | 'Mitigating' | 'Resolved';
export const CaseStatus = {
  Open: 'Open',
  Investigating: 'Investigating',
  Mitigating: 'Mitigating',
  Resolved: 'Resolved',
} as const;

export type ExposureBand = 'Regulatory' | 'Financial' | 'Privacy' | 'Operational';
export const ExposureBand = {
  Regulatory: 'Regulatory',
  Financial: 'Financial',
  Privacy: 'Privacy',
  Operational: 'Operational',
} as const;

export type RootCause = 'Misconfig' | 'Legit Load' | 'External Dependency' | 'Unknown';
export const RootCause = {
  Misconfig: 'Misconfig',
  LegitLoad: 'Legit Load',
  ExternalDependency: 'External Dependency',
  Unknown: 'Unknown',
} as const;

export type RiskFlag =
  | 'retry_loop'
  | 'unbounded_iterator'
  | 'missing_idempotency'
  | 'sudden_prompt_growth'
  | 'deployment_correlation'
  | 'batch_job'
  | 'backfill_mode'
  | 'linear_scaling'
  | 'pii_exposure'
  | 'regulatory_data';

export type PolicyAction =
  | 'quarantine'
  | 'block_dispatch'
  | 'create_case'
  | 'page_lock'
  | 'slack_escalate'
  | 'slack_alert'
  | 'require_ack_before_rerun'
  | 'require_ack'
  | 'log_case_optional'
  | 'weekly_review'
  | 'ledger_only'
  | 'weekly_review_optional';

export interface SeverityPolicyConfig {
  multiplier: number;
  pii_or_regulatory?: boolean;
  action: PolicyAction[];
}

export interface RiskFlagConfig {
  misconfig_weight?: number;
  legit_weight?: number;
}

/**
 * Upstream monitoring policy model.
 */
export interface MonitoringPolicy {
  version: string;
  severity_policy: Record<string, any>;
  risk_flags: Record<string, RiskFlagConfig>;
  thresholds: {
    max_retries: number;
    quarantine_credit_multiplier: number;
    high_misconfig_score: number;
  };
  review_windows?: {
    credit_review_days: number;
    baseline_window_days: number;
    healthy_run_statuses: string[];
  };
  slack?: {
    channels: {
      sev0: string;
      sev1: string;
      sev2: string;
      default: string;
    };
  };
  notion?: {
    databases: {
      runs_ledger_id: string;
      cases_id: string;
    };
  };
}

/**
 * Legacy policy config used by the older severity-classifier implementation.
 */
export interface PolicyConfig {
  version: string;
  severity_policy: {
    sev0: SeverityPolicyConfig;
    sev1: SeverityPolicyConfig;
    sev2: SeverityPolicyConfig;
    sev3: SeverityPolicyConfig;
    sev4: SeverityPolicyConfig;
  };
  risk_flags: Record<string, RiskFlagConfig>;
}

/**
 * Upstream (snake_case) run record.
 */
export interface RunRecord {
  run_id: string;
  timestamp: string;
  scenario_name: string;
  scenario_id: string;
  job_type: JobType;
  status: RunStatus;
  credits_total: number;
  credits_in?: number;
  credits_out?: number;
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  artifacts_link?: string;
  notion_case_id?: string;
  severity: Severity;
  risk_flags: string[];
  risk_summary?: string;
  misconfig_likelihood: MisconfigLikelihood;
  baseline_expected_credits: number;
  variance_multiplier: number;
  owner: string;

  // Optional metadata used by some classifiers
  retry_count?: number;
  has_max_items_config?: boolean;
  has_idempotency_key?: boolean;
  prompt_version?: string;
  deployment_timestamp?: string;
  is_batch_job?: boolean;
  is_backfill?: boolean;
  input_item_count?: number;
}

/**
 * Legacy (PascalCase) run record used by older monitoring modules.
 */
export interface RunRecordLegacy {
  Run_ID: string;
  Timestamp: string;
  Scenario_Name: string;
  Scenario_ID?: string;
  Job_Type: JobType;
  Status: RunStatus;
  Credits_Total: number;
  Credits_In?: number;
  Credits_Out?: number;
  Model?: string;
  Input_Tokens?: number;
  Output_Tokens?: number;
  Artifacts_Link?: string;
  Severity: Severity;
  Risk_Flags?: RiskFlag[];
  Risk_Summary?: string;
  Misconfig_Likelihood: MisconfigLikelihood;
  Baseline_Expected_Credits?: number;
  Variance_Multiplier: number;

  retry_count?: number;
  has_max_items_config?: boolean;
  has_idempotency_key?: boolean;
  prompt_version?: string;
  deployment_timestamp?: string;
  is_batch_job?: boolean;
  is_backfill?: boolean;
  input_item_count?: number;
}

export interface CaseRecord {
  case_id: string;
  title: string;
  category: CaseCategory;
  severity: Severity;
  exposure_band: ExposureBand;
  status: CaseStatus;
  primary_run_id?: string;
  run_timeline_ids: string[];
  slack_thread_url?: string;
  root_cause?: RootCause;
  fix_patch?: string;
  prevent_recurrence_notes?: string;
  prevent_recurrence_complete?: boolean;
}

export interface CaseRecordLegacy {
  Case_ID: string;
  Title: string;
  Category: CaseCategory;
  Severity: Severity;
  Exposure_Band: ExposureBand;
  Status: CaseStatus;
  Slack_Thread_URL?: string;
  Root_Cause?: RootCause;

  Primary_Run_ID?: string;
  Related_Run_IDs?: string[];

  Created_At?: string;
  Updated_At?: string;
  Resolved_At?: string;

  notion_url?: string;
}

export interface Classification {
  severity: Severity;
  misconfigLikelihood: MisconfigLikelihood;
  riskFlags: RiskFlag[];
  varianceMultiplier: number;
  misconfigScore: number;
  legitScore: number;
  actions: PolicyAction[];
}

export interface MisconfigAssessment {
  likelihood: MisconfigLikelihood;
  score: number;
  signals: {
    misconfig: Array<{ flag: RiskFlag; weight: number }>;
    legit: Array<{ flag: RiskFlag; weight: number }>;
  };
}

export interface BaselineData {
  scenario_id: string;
  median_credits: number;
  calculated_at: string;
  sample_size: number;
  last_updated: string;
}

export interface ScenarioSummary {
  scenario_id: string;
  total_credits: number;
  run_count: number;
  avg_credits: number;
  baseline: number;
  variance_multiplier: number;
  p95_credits?: number;
  max_credits?: number;
}

export interface CreditReport {
  report_id: string;
  period_start: string;
  period_end: string;
  top_scenarios_by_total: ScenarioSummary[];
  top_spike_runs: RunRecordLegacy[];
  baseline_candidates: ScenarioSummary[];
  policy_violations: Array<{
    run_id: string;
    violation_type: string;
    severity: Severity;
  }>;
  summary_stats: {
    total_credits: number;
    total_runs: number;
    avg_credits_per_run: number;
    sev0_count: number;
    sev1_count: number;
    sev2_count: number;
  };
}

export interface SlackMessage {
  blocks: SlackBlock[];
  text?: string;
}

export type SlackBlock =
  | SlackHeaderBlock
  | SlackSectionBlock
  | SlackActionsBlock
  | SlackContextBlock
  | SlackDividerBlock;

export interface SlackHeaderBlock {
  type: 'header';
  text: {
    type: 'plain_text';
    text: string;
    emoji?: boolean;
  };
}

export interface SlackSectionBlock {
  type: 'section';
  text?: {
    type: 'mrkdwn' | 'plain_text';
    text: string;
  };
  fields?: Array<{
    type: 'mrkdwn' | 'plain_text';
    text: string;
  }>;
}

export interface SlackActionsBlock {
  type: 'actions';
  elements: Array<{
    type: 'button';
    text: {
      type: 'plain_text';
      text: string;
      emoji?: boolean;
    };
    url?: string;
    value?: string;
    style?: 'primary' | 'danger';
  }>;
}

export interface SlackContextBlock {
  type: 'context';
  elements: Array<{
    type: 'mrkdwn' | 'plain_text' | 'image';
    text?: string;
    image_url?: string;
    alt_text?: string;
  }>;
}

export interface SlackDividerBlock {
  type: 'divider';
}
