/**
 * Case Manager
 * Creates and updates Notion CASES with run linkage
 * 
 * Responsibilities:
 * - Generate unique Case_ID
 * - Create Notion case pages
 * - Link runs to cases
 * - Determine exposure bands
 */

import crypto from "crypto";
import {
  CaseCategory,
  CaseStatus,
  ExposureBand,
  type CaseRecordLegacy as CaseRecord,
  type RiskFlag,
  type RootCause,
  type RunRecordLegacy as RunRecord,
  type SeverityLevel,
} from "./types.js";

/**
 * Create a new case for a run
 */
export async function createCase(
  runRecord: RunRecord,
  severity: SeverityLevel,
  riskFlags: RiskFlag[]
): Promise<CaseRecord> {
  const caseId = generateCaseId();
  const category = determineCaseCategory(riskFlags);
  const exposureBand = determineExposureBand(riskFlags, severity);
  
  const caseRecord: CaseRecord = {
    Case_ID: caseId,
    Title: `${severity} • Credit Spike • ${runRecord.Scenario_Name}`,
    Category: category,
    Severity: severity,
    Exposure_Band: exposureBand,
    Status: CaseStatus.Open,
    Primary_Run_ID: runRecord.Run_ID,
    Related_Run_IDs: [runRecord.Run_ID],
    Created_At: new Date().toISOString(),
  };

  // Write to Notion (stub)
  const notionUrl = await writeToNotion(caseRecord);
  caseRecord.notion_url = notionUrl;

  console.log(`[case-manager] Created case ${caseId} for run ${runRecord.Run_ID}`);
  
  return caseRecord;
}

/**
 * Link an additional run to an existing case
 */
export async function linkRunToCase(
  runId: string,
  caseId: string
): Promise<void> {
  console.log(`[case-manager] Linking run ${runId} to case ${caseId}`);
  
  // This would update the Notion case page to add the run to Related_Run_IDs
  // For now, just log the action
}

/**
 * Generate a unique Case ID in format CASE-YYYYMMDD-XXXXXX
 */
function generateCaseId(): string {
  const date = new Date();
  const dateStr = date.toISOString().slice(0, 10).replace(/-/g, ""); // YYYYMMDD
  
  // Generate 6-character random alphanumeric suffix
  const suffix = crypto.randomBytes(3).toString("hex").toUpperCase();
  
  return `CASE-${dateStr}-${suffix}`;
}

/**
 * Determine case category based on risk flags
 */
function determineCaseCategory(riskFlags: RiskFlag[]): CaseCategory {
  if (riskFlags.includes("pii_exposure")) {
    return CaseCategory.DataPII;
  }
  
  if (riskFlags.includes("regulatory_data")) {
    return CaseCategory.FilingRegulatory;
  }
  
  // Default to Cost/Credits for credit spikes
  return CaseCategory.CostCredits;
}

/**
 * Determine exposure band based on risk flags and severity
 */
function determineExposureBand(
  riskFlags: RiskFlag[],
  severity: SeverityLevel
): ExposureBand {
  if (riskFlags.includes("pii_exposure") || riskFlags.includes("regulatory_data")) {
    return severity === "SEV0" ? ExposureBand.Regulatory : ExposureBand.Privacy;
  }
  
  if (severity === "SEV0" || severity === "SEV1") {
    return ExposureBand.Financial;
  }
  
  return ExposureBand.Operational;
}

/**
 * Write case to Notion (stub)
 */
async function writeToNotion(caseRecord: CaseRecord): Promise<string> {
  // This would use Notion API to create a case page
  // For now, return a mock URL
  const mockUrl = `https://notion.so/case-${caseRecord.Case_ID}`;
  console.log(`[case-manager] Would write to Notion: ${mockUrl}`);
  return mockUrl;
}

/**
 * Update case status
 */
export async function updateCaseStatus(
  caseId: string,
  status: CaseStatus,
  rootCause?: RootCause
): Promise<void> {
  console.log(`[case-manager] Updating case ${caseId} to status ${status}`);
  
  if (rootCause) {
    console.log(`[case-manager] Setting root cause: ${rootCause}`);
  }
  
  // This would update the Notion case page
}

/**
 * Add Slack thread URL to case
 */
export async function updateCaseSlackThread(
  caseId: string,
  slackThreadUrl: string
): Promise<void> {
  console.log(`[case-manager] Adding Slack thread to case ${caseId}: ${slackThreadUrl}`);
  
  // This would update the Notion case page
}
