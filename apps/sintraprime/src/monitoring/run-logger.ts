/**
 * Run Logger
 * Writes run records to Notion RUNS_LEDGER and local audit trail
 * 
 * Implements audit-first pattern:
 * - Write to local JSON with .sha256 sidecar
 * - Append to ledger.jsonl (append-only)
 * - Optionally sync to Notion
 */

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import type { RunRecordLegacy as RunRecord } from "./types.js";

/**
 * Log a run to the audit trail and optionally to Notion
 */
export async function logRun(runData: RunRecord): Promise<void> {
  const timestamp = new Date(runData.Timestamp);
  const dateStr = timestamp.toISOString().slice(0, 10); // YYYY-MM-DD
  
  // Create directory structure
  const runDir = path.join(process.cwd(), "runs", "CREDIT_MONITORING", dateStr);
  fs.mkdirSync(runDir, { recursive: true });

  // Write run JSON
  const runFile = path.join(runDir, `run_${runData.Run_ID}.json`);
  const runJson = JSON.stringify(runData, null, 2);
  fs.writeFileSync(runFile, runJson, "utf-8");

  // Generate .sha256 sidecar
  const sha256 = crypto.createHash("sha256").update(runJson).digest("hex");
  const sha256File = `${runFile}.sha256`;
  fs.writeFileSync(sha256File, sha256, "utf-8");

  // Append to ledger.jsonl
  const ledgerFile = path.join(process.cwd(), "runs", "CREDIT_MONITORING", "ledger.jsonl");
  const ledgerEntry = JSON.stringify(runData) + "\n";
  fs.appendFileSync(ledgerFile, ledgerEntry, "utf-8");

  console.log(`[run-logger] Logged run ${runData.Run_ID} to ${runFile}`);
  console.log(`[run-logger] SHA-256: ${sha256}`);

  // Optional: Write to Notion (would require Notion API integration)
  if (process.env.NOTION_RUNS_LEDGER_DB_ID) {
    await writeToNotion(runData);
  }
}

/**
 * Write run record to Notion database (stub for now)
 */
async function writeToNotion(runData: RunRecord): Promise<void> {
  // This would integrate with Notion API
  // For now, just log that it would be written
  console.log(`[run-logger] Would write to Notion: ${runData.Run_ID}`);
  
  // In production, this would use @notionhq/client:
  // const notion = new Client({ auth: process.env.NOTION_TOKEN });
  // await notion.pages.create({
  //   parent: { database_id: process.env.NOTION_RUNS_LEDGER_DB_ID },
  //   properties: { ... }
  // });
}

/**
 * Read runs from ledger within a date range
 */
export function readRunsFromLedger(
  startDate: Date,
  endDate: Date
): RunRecord[] {
  const ledgerFile = path.join(process.cwd(), "runs", "CREDIT_MONITORING", "ledger.jsonl");
  
  if (!fs.existsSync(ledgerFile)) {
    return [];
  }

  const content = fs.readFileSync(ledgerFile, "utf-8");
  const lines = content.split("\n").filter(line => line.trim());
  
  const runs: RunRecord[] = [];
  for (const line of lines) {
    try {
      const run = JSON.parse(line) as RunRecord;
      const runDate = new Date(run.Timestamp);
      
      if (runDate >= startDate && runDate <= endDate) {
        runs.push(run);
      }
    } catch (err) {
      console.error(`[run-logger] Failed to parse ledger line: ${err}`);
    }
  }
  
  return runs;
}

/**
 * Get runs by scenario ID
 */
export function getRunsByScenario(
  scenarioId: string,
  limit?: number
): RunRecord[] {
  const ledgerFile = path.join(process.cwd(), "runs", "CREDIT_MONITORING", "ledger.jsonl");
  
  if (!fs.existsSync(ledgerFile)) {
    return [];
  }

  const content = fs.readFileSync(ledgerFile, "utf-8");
  const lines = content.split("\n").filter(line => line.trim());
  
  const runs: RunRecord[] = [];
  for (const line of lines) {
    try {
      const run = JSON.parse(line) as RunRecord;
      
      if (run.Scenario_ID === scenarioId) {
        runs.push(run);
        if (limit && runs.length >= limit) {
          break;
        }
      }
    } catch (err) {
      console.error(`[run-logger] Failed to parse ledger line: ${err}`);
    }
  }
  
  return runs;
}

/**
 * Verify a run artifact's SHA-256
 */
export function verifyRunArtifact(runId: string, dateStr: string): boolean {
  const runDir = path.join(process.cwd(), "runs", "CREDIT_MONITORING", dateStr);
  const runFile = path.join(runDir, `run_${runId}.json`);
  const sha256File = `${runFile}.sha256`;

  if (!fs.existsSync(runFile) || !fs.existsSync(sha256File)) {
    return false;
  }

  const content = fs.readFileSync(runFile, "utf-8");
  const expectedSha = fs.readFileSync(sha256File, "utf-8").trim();
  const actualSha = crypto.createHash("sha256").update(content).digest("hex");

  return expectedSha === actualSha;
}
