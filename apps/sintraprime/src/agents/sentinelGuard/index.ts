// src/agents/sentinelGuard/index.ts
// Barrel export for the SentinelGuard cybersecurity agent module.

export { SentinelGuardAgent } from "./sentinelGuardAgent.js";
export type { SentinelGuardConfig } from "./sentinelGuardAgent.js";

export { InputAnalyzer } from "./inputAnalyzer.js";
export type { AnalysisResult } from "./inputAnalyzer.js";

export { IncidentManager } from "./incidentManager.js";
export type {
  SecurityIncident,
  IncidentSeverity,
  IncidentStatus,
  IncidentTimelineEntry,
} from "./incidentManager.js";

export { SecurityKnowledgeBase } from "./securityKnowledgeBase.js";
export type {
  DiscoveredAsset,
  ServiceInfo,
  VulnerabilityRecord,
} from "./securityKnowledgeBase.js";
