// src/agents/sentinelGuard/sentinelGuardAgent.ts
// The core SentinelGuard agent class, extended with PentAGI-inspired capabilities.
// This agent operates as a persistent background service and is the central
// coordinator for all security operations within SintraPrime.

import { ReceiptLedger } from "../../audit/receiptLedger.js";
import { PolicyGate } from "../../governance/policyGate.js";
import { JobScheduler } from "../../scheduler/jobScheduler.js";
import { NmapAdapter } from "../../tools/security/NmapAdapter.js";
import { OsintTool } from "../../tools/security/OsintTool.js";
import { PentestReportTool } from "../../tools/security/PentestReportTool.js";
import type { ActionReceipt } from "../../types/index.js";
import crypto from "crypto";

export interface SentinelGuardConfig {
  receiptLedger: ReceiptLedger;
  policyGate: PolicyGate;
  scheduler?: JobScheduler;
  networkScanTargets?: string[];    // e.g., ["10.0.1.0/24", "192.168.1.0/24"]
  scanSchedule?: string;            // Cron expression, e.g., "0 2 * * 0" (Sunday 2am)
  alertWebhook?: string;            // Webhook URL for security alerts
}

export class SentinelGuardAgent {
  private readonly receiptLedger: ReceiptLedger;
  private readonly policyGate: PolicyGate;
  private readonly scheduler?: JobScheduler;
  private readonly config: SentinelGuardConfig;
  private readonly nmapAdapter: NmapAdapter;
  private readonly osintTool: OsintTool;
  private readonly reportTool: PentestReportTool;
  private isRunning = false;

  constructor(config: SentinelGuardConfig) {
    this.config = config;
    this.receiptLedger = config.receiptLedger;
    this.policyGate = config.policyGate;
    this.scheduler = config.scheduler;
    this.nmapAdapter = new NmapAdapter();
    this.osintTool = new OsintTool();
    this.reportTool = new PentestReportTool(this.receiptLedger);
  }

  /**
   * Start SentinelGuard. Called during system initialization in src/index.ts.
   * Registers scheduled jobs and begins monitoring.
   */
  async start(): Promise<void> {
    if (this.isRunning) return;
    this.isRunning = true;

    await this.recordOwnAction("sentinel_guard.start", {
      version: "2.0.0",
      capabilities: [
        "security.vulnerability.scan.network",
        "security.osint.gather",
        "security.pentest.run",
        "security.report.generate",
      ],
    });

    // Register scheduled vulnerability scan if scheduler and targets are configured.
    if (this.scheduler && this.config.networkScanTargets?.length) {
      this.scheduler.scheduleJob({
        id: "sentinel-guard-weekly-network-scan",
        name: "SentinelGuard Weekly Network Vulnerability Scan",
        schedule: this.config.scanSchedule || "0 2 * * 0",
        task: { type: "security.vulnerability.scan.network" },
        enabled: true,
      });
      console.log("[SentinelGuard] Registered weekly network scan job.");
    }

    console.log("[SentinelGuard] Started and monitoring.");
  }

  /**
   * Stop SentinelGuard gracefully.
   */
  async stop(): Promise<void> {
    this.isRunning = false;
    await this.recordOwnAction("sentinel_guard.stop", { reason: "graceful_shutdown" });
    console.log("[SentinelGuard] Stopped.");
  }

  /**
   * Returns whether SentinelGuard is currently running.
   */
  getStatus(): { running: boolean; version: string } {
    return { running: this.isRunning, version: "2.0.0" };
  }

  /**
   * PRE-EXECUTION HOOK: Called by the Orchestrator before executing a plan.
   * Reviews the plan for security concerns and can block or flag suspicious steps.
   */
  async reviewPlan(plan: {
    id: string;
    steps: Array<{ id: string; tool: string; args?: any }>;
  }): Promise<{ approved: boolean; concerns: string[] }> {
    const concerns: string[] = [];
    const highRiskTools = ["metasploit_exploit", "sqlmap_scan", "hydra_attack"];

    for (const step of plan.steps) {
      if (highRiskTools.includes(step.tool)) {
        concerns.push(
          `High-risk tool '${step.tool}' in step '${step.id}' requires explicit approval.`
        );
      }
      // Check for unusual tool combinations (e.g., data exfiltration after a scan)
      if (
        step.tool === "google_drive_upload" &&
        plan.steps.some((s) => highRiskTools.includes(s.tool))
      ) {
        concerns.push(
          `Suspicious combination: data upload following a high-risk security tool in plan '${plan.id}'.`
        );
      }
    }

    await this.recordOwnAction("sentinel_guard.plan_review", {
      planId: plan.id,
      stepCount: plan.steps.length,
      concerns,
      approved: concerns.length === 0,
    });

    return { approved: concerns.length === 0, concerns };
  }

  /**
   * POST-EXECUTION HOOK: Called by the Executor after each step completes.
   * Analyzes the ActionReceipt for anomalies and threats.
   */
  async analyzeReceipt(receipt: ActionReceipt): Promise<void> {
    // Detect anomalous patterns in real time.
    const anomalies: string[] = [];

    // Example: Detect if a tool is being called at an unusual hour.
    const hour = new Date(receipt.timestamp).getUTCHours();
    if (hour >= 2 && hour <= 5 && receipt.action.startsWith("tool.")) {
      anomalies.push(
        `Unusual activity: tool '${receipt.action}' called between 02:00-05:00 UTC.`
      );
    }

    // Example: Detect if a large number of receipts are being generated rapidly.
    const recentReceipts = this.receiptLedger.getReceiptsInRange(
      new Date(Date.now() - 60000).toISOString(),
      new Date().toISOString()
    );
    if (recentReceipts.length > 50) {
      anomalies.push(
        `High activity rate: ${recentReceipts.length} actions in the last 60 seconds.`
      );
    }

    if (anomalies.length > 0) {
      await this.createIncident("ANOMALY_DETECTED", anomalies, receipt);
    }
  }

  /**
   * Runs a scheduled network vulnerability scan.
   * Called by the JobScheduler on the configured cron schedule.
   */
  async runScheduledNetworkScan(): Promise<void> {
    const targets = this.config.networkScanTargets || [];
    if (!targets.length) return;

    console.log(
      `[SentinelGuard] Starting scheduled network scan for ${targets.length} target(s).`
    );

    for (const target of targets) {
      try {
        const result = await this.nmapAdapter.execute({
          target,
          options: "-sV -sC",
        });
        await this.recordOwnAction("sentinel_guard.network_scan_complete", {
          target,
          hostsFound: result.findings.length,
          openPortsTotal: result.findings.reduce(
            (acc, f) => acc + f.openPorts.length,
            0
          ),
        });
        console.log(
          `[SentinelGuard] Scan complete for ${target}: ${result.findings.length} hosts found.`
        );
      } catch (error: any) {
        console.error(
          `[SentinelGuard] Scan failed for target ${target}:`,
          error.message
        );
        await this.recordOwnAction("sentinel_guard.network_scan_failed", {
          target,
          error: error.message,
        });
      }
    }
  }

  /**
   * Run an OSINT gathering operation on a target domain.
   */
  async runOsintGather(domain: string, sources?: string[]): Promise<any> {
    try {
      const result = await this.osintTool.execute({ domain, sources });
      await this.recordOwnAction("sentinel_guard.osint_complete", {
        domain,
        emailsFound: result.emails.length,
        subdomainsFound: result.subdomains.length,
      });
      return result;
    } catch (error: any) {
      await this.recordOwnAction("sentinel_guard.osint_failed", {
        domain,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Generate a penetration test report for a given engagement.
   */
  async generateReport(
    engagementId: string,
    startTime: string,
    endTime: string,
    targetScope: string[]
  ): Promise<any> {
    return this.reportTool.execute({
      engagementId,
      startTime,
      endTime,
      targetScope,
      outputFormat: "markdown",
    });
  }

  /**
   * Creates a security incident record in the ReceiptLedger and triggers alerting.
   */
  private async createIncident(
    type: string,
    details: string[],
    relatedReceipt?: ActionReceipt
  ): Promise<void> {
    const incidentId = `incident-${crypto.randomUUID()}`;
    await this.recordOwnAction("sentinel_guard.incident_created", {
      incidentId,
      type,
      details,
      relatedReceiptId: relatedReceipt?.id,
      severity: "HIGH",
      status: "OPEN",
    });
    console.warn(
      `[SentinelGuard] INCIDENT CREATED [${type}]: ${details.join("; ")}`
    );

    // Send alert to webhook if configured
    if (this.config.alertWebhook) {
      try {
        const body = JSON.stringify({
          text: `[SentinelGuard INCIDENT] ${type}: ${details.join("; ")}`,
          incidentId,
          severity: "HIGH",
        });
        await fetch(this.config.alertWebhook, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
        });
      } catch (err: any) {
        console.error(
          `[SentinelGuard] Failed to send alert webhook: ${err.message}`
        );
      }
    }
  }

  /**
   * Records SentinelGuard's own actions in the ReceiptLedger for full transparency.
   */
  private async recordOwnAction(action: string, result: any): Promise<void> {
    const data = {
      id: crypto.randomUUID(),
      actor: "agent:sentinel-guard-agent/v2.0.0",
      action,
      result,
    };
    const hash = crypto
      .createHash("sha256")
      .update(JSON.stringify(data))
      .digest("hex");
    await this.receiptLedger.recordAction({
      id: data.id,
      toolCallId: `sentinel-internal-${Date.now()}`,
      actor: data.actor,
      action: data.action,
      timestamp: new Date().toISOString(),
      result: data.result,
      hash,
    });
  }
}
