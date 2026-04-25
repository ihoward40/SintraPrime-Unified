// src/agents/sentinelGuard/incidentManager.ts
// Manages the lifecycle of security incidents: create, update, close, escalate.
// All incident state changes are recorded in the ReceiptLedger for auditability.

import { ReceiptLedger } from "../../audit/receiptLedger.js";
import crypto from "crypto";

export type IncidentSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type IncidentStatus = "OPEN" | "INVESTIGATING" | "CONTAINED" | "RESOLVED" | "CLOSED";

export interface SecurityIncident {
  id: string;
  type: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  title: string;
  description: string;
  details: string[];
  relatedReceiptIds: string[];
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  assignee?: string;
  containmentActions: string[];
  timeline: IncidentTimelineEntry[];
}

export interface IncidentTimelineEntry {
  timestamp: string;
  action: string;
  actor: string;
  details: string;
}

export class IncidentManager {
  private incidents: Map<string, SecurityIncident> = new Map();
  private readonly receiptLedger: ReceiptLedger;

  constructor(receiptLedger: ReceiptLedger) {
    this.receiptLedger = receiptLedger;
  }

  /**
   * Create a new security incident.
   */
  async createIncident(params: {
    type: string;
    severity: IncidentSeverity;
    title: string;
    description: string;
    details: string[];
    relatedReceiptIds?: string[];
  }): Promise<SecurityIncident> {
    const now = new Date().toISOString();
    const incident: SecurityIncident = {
      id: `incident-${crypto.randomUUID()}`,
      type: params.type,
      severity: params.severity,
      status: "OPEN",
      title: params.title,
      description: params.description,
      details: params.details,
      relatedReceiptIds: params.relatedReceiptIds || [],
      createdAt: now,
      updatedAt: now,
      containmentActions: [],
      timeline: [
        {
          timestamp: now,
          action: "CREATED",
          actor: "agent:sentinel-guard-agent/v2.0.0",
          details: `Incident created: ${params.title}`,
        },
      ],
    };

    this.incidents.set(incident.id, incident);
    await this.recordIncidentAction("incident.created", incident);

    console.warn(
      `[IncidentManager] INCIDENT CREATED [${incident.severity}] ${incident.id}: ${incident.title}`
    );

    return incident;
  }

  /**
   * Update an existing incident's status.
   */
  async updateStatus(
    incidentId: string,
    newStatus: IncidentStatus,
    details: string
  ): Promise<SecurityIncident | null> {
    const incident = this.incidents.get(incidentId);
    if (!incident) {
      console.error(`[IncidentManager] Incident not found: ${incidentId}`);
      return null;
    }

    const now = new Date().toISOString();
    incident.status = newStatus;
    incident.updatedAt = now;

    if (newStatus === "RESOLVED" || newStatus === "CLOSED") {
      incident.resolvedAt = now;
    }

    incident.timeline.push({
      timestamp: now,
      action: `STATUS_CHANGED:${newStatus}`,
      actor: "agent:sentinel-guard-agent/v2.0.0",
      details,
    });

    await this.recordIncidentAction("incident.status_updated", {
      incidentId,
      newStatus,
      details,
    });

    return incident;
  }

  /**
   * Add a containment action to an incident.
   */
  async addContainmentAction(
    incidentId: string,
    action: string
  ): Promise<void> {
    const incident = this.incidents.get(incidentId);
    if (!incident) return;

    const now = new Date().toISOString();
    incident.containmentActions.push(action);
    incident.updatedAt = now;

    incident.timeline.push({
      timestamp: now,
      action: "CONTAINMENT_ACTION",
      actor: "agent:sentinel-guard-agent/v2.0.0",
      details: action,
    });

    await this.recordIncidentAction("incident.containment_action", {
      incidentId,
      action,
    });
  }

  /**
   * Escalate an incident to a higher severity.
   */
  async escalate(
    incidentId: string,
    newSeverity: IncidentSeverity,
    reason: string
  ): Promise<SecurityIncident | null> {
    const incident = this.incidents.get(incidentId);
    if (!incident) return null;

    const now = new Date().toISOString();
    const oldSeverity = incident.severity;
    incident.severity = newSeverity;
    incident.updatedAt = now;

    incident.timeline.push({
      timestamp: now,
      action: `ESCALATED:${oldSeverity}->${newSeverity}`,
      actor: "agent:sentinel-guard-agent/v2.0.0",
      details: reason,
    });

    await this.recordIncidentAction("incident.escalated", {
      incidentId,
      oldSeverity,
      newSeverity,
      reason,
    });

    console.warn(
      `[IncidentManager] INCIDENT ESCALATED ${incidentId}: ${oldSeverity} -> ${newSeverity}`
    );

    return incident;
  }

  /**
   * Get an incident by ID.
   */
  getIncident(incidentId: string): SecurityIncident | undefined {
    return this.incidents.get(incidentId);
  }

  /**
   * Get all open incidents.
   */
  getOpenIncidents(): SecurityIncident[] {
    return Array.from(this.incidents.values()).filter(
      (i) => i.status !== "CLOSED" && i.status !== "RESOLVED"
    );
  }

  /**
   * Get all incidents by severity.
   */
  getIncidentsBySeverity(severity: IncidentSeverity): SecurityIncident[] {
    return Array.from(this.incidents.values()).filter(
      (i) => i.severity === severity
    );
  }

  /**
   * Record incident actions in the ReceiptLedger for auditability.
   */
  private async recordIncidentAction(action: string, data: any): Promise<void> {
    const id = crypto.randomUUID();
    const hash = crypto
      .createHash("sha256")
      .update(JSON.stringify({ id, action, data }))
      .digest("hex");

    await this.receiptLedger.recordAction({
      id,
      toolCallId: `incident-mgr-${Date.now()}`,
      actor: "agent:sentinel-guard-agent/v2.0.0",
      action,
      timestamp: new Date().toISOString(),
      result: data,
      hash,
    });
  }
}
