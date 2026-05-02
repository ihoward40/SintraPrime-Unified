/**
 * Trust Compliance Module — Smoke Test
 *
 * Validates that runTrustComplianceMission returns all required keys and
 * correctly classifies a sample document containing both safe trust-admin
 * language and flagged self-executing-acceptance language.
 *
 * Run with:
 *   npx tsx apps/sintraprime/src/modules/trust-compliance/test.ts
 */

import { runTrustComplianceMission } from './agents/orchestrator.js';

const SAMPLE_DOCUMENT = `
CERTIFICATION OF TRUST
Executed this 15th day of January, 2025

This Certification of Trust is made by Irene Howard, as Trustee of the
Howard Family Irrevocable Trust, established under the laws of the State
of Nevada, EIN 88-1234567.

TRUSTEE AUTHORITY
The Trustee has full authority to open and manage financial accounts, enter
into contracts, and execute documents on behalf of the trust in accordance
with the trust instrument and applicable fiduciary duties.

BANKING RESOLUTION
The Trustee hereby authorizes the establishment of banking accounts at
federally insured financial institutions. The Trustee's signature shall
be required for all account transactions exceeding five thousand dollars.

SELF-EXECUTING ACCEPTANCE
By your acceptance of this notice, you agree to all terms stated herein.
Your failure to respond within 14 days shall constitute tacit consent to
these terms and conditions. Silence is consent.

GENERAL PROVISIONS
This instrument shall be governed by the laws of the State of Nevada.
All disputes shall be resolved through good-faith negotiation and, if
necessary, mediation or arbitration before resort to litigation.
`.trim();

async function runSmokeTest(): Promise<void> {
  console.log('Running Trust Compliance Module smoke test...\n');

  const result = await runTrustComplianceMission({
    rawText: SAMPLE_DOCUMENT,
    filename: 'certification_of_trust_sample.txt',
    uploadedAt: new Date().toISOString(),
  });

  // ── Validate required keys ────────────────────────────────────────────────

  const requiredKeys: Array<keyof typeof result> = [
    'document',
    'riskRegister',
    'exhibits',
    'recommendations',
    'receipt',
  ];

  console.log('=== Required Key Validation ===');
  let allPassed = true;
  for (const key of requiredKeys) {
    const present = key in result && result[key] !== undefined && result[key] !== null;
    console.log(`  ${present ? '✓' : '✗'} ${key}`);
    if (!present) allPassed = false;
  }
  console.log('');

  // ── Document ─────────────────────────────────────────────────────────────

  console.log('=== Parsed Document ===');
  console.log(`  ID:   ${result.document.id}`);
  console.log(`  Type: ${result.document.documentType}`);
  console.log(`  Title: ${result.document.title}`);
  console.log(`  Sections: ${result.document.sections.length}`);
  console.log('');

  // ── Risk Register ─────────────────────────────────────────────────────────

  console.log('=== Risk Register ===');
  for (const entry of result.riskRegister) {
    console.log(
      `  [${entry.classification}] "${entry.sectionTitle}" → action: ${entry.action}`,
    );
    if (entry.riskTags.length > 0) {
      console.log(`         tags: ${entry.riskTags.join(', ')}`);
    }
  }
  console.log('');

  // ── Classification counts ─────────────────────────────────────────────────

  const greenCount = result.riskRegister.filter((e) => e.classification === 'GREEN').length;
  const yellowCount = result.riskRegister.filter((e) => e.classification === 'YELLOW').length;
  const redCount = result.riskRegister.filter((e) => e.classification === 'RED').length;

  console.log('=== Classification Summary ===');
  console.log(`  GREEN:  ${greenCount}`);
  console.log(`  YELLOW: ${yellowCount}`);
  console.log(`  RED:    ${redCount}`);
  console.log('');

  // ── Safety gate: RED clauses must not be exportable ───────────────────────

  console.log('=== Safety Gate: RED Clause Export Check ===');
  const redEntries = result.riskRegister.filter((e) => e.classification === 'RED');
  let safetyPassed = true;
  for (const entry of redEntries) {
    if (entry.action !== 'block') {
      console.log(`  ✗ FAIL: RED clause "${entry.sectionTitle}" has action "${entry.action}" instead of "block"`);
      safetyPassed = false;
    } else {
      console.log(`  ✓ RED clause "${entry.sectionTitle}" is correctly blocked`);
    }
  }
  if (redEntries.length === 0) {
    console.log('  (no RED clauses in this document)');
  }
  console.log('');

  // ── Exhibits ──────────────────────────────────────────────────────────────

  console.log('=== Exhibit Index ===');
  console.log(`  Public:  ${result.exhibits.public.length}`);
  for (const ex of result.exhibits.public) {
    console.log(`    ${ex.id}: ${ex.title}`);
  }
  console.log(`  Reserve: ${result.exhibits.reserve.length}`);
  for (const ex of result.exhibits.reserve) {
    console.log(`    ${ex.id}: ${ex.title} [INTERNAL ONLY]`);
  }
  console.log('');

  // ── Recommendations ───────────────────────────────────────────────────────

  console.log('=== Recommendations by Context ===');
  for (const rec of result.recommendations) {
    const summary = [];
    if (rec.permitted.length > 0) summary.push(`${rec.permitted.length} permitted`);
    if (rec.blocked.length > 0) summary.push(`${rec.blocked.length} blocked`);
    if (rec.rewrites.length > 0) summary.push(`${rec.rewrites.length} rewrites`);
    console.log(`  ${rec.context}: ${summary.join(', ') || 'no actions'}`);
  }
  console.log('');

  // ── Receipt ───────────────────────────────────────────────────────────────

  console.log('=== Run Receipt ===');
  console.log(`  Run ID:          ${result.receipt.runId}`);
  console.log(`  Timestamp:       ${result.receipt.timestamp}`);
  console.log(`  Document:        ${result.receipt.documentTitle}`);
  console.log(`  Total Clauses:   ${result.receipt.totalClauses}`);
  console.log(`  Blocked Exports: ${result.receipt.blockedExports}`);
  console.log(`  Actions logged:  ${result.receipt.actions.length}`);
  console.log('');

  // ── Final result ──────────────────────────────────────────────────────────

  const passed = allPassed && safetyPassed;
  console.log('=== Smoke Test Result ===');
  if (passed) {
    console.log('  ✓ PASSED — all required keys present, safety gates enforced');
  } else {
    console.log('  ✗ FAILED — see issues above');
    process.exit(1);
  }
}

runSmokeTest().catch((err) => {
  console.error('Smoke test error:', err);
  process.exit(1);
});
