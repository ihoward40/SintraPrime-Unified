// src/agents/sentinelGuard/securityKnowledgeBase.ts
// Queryable model of discovered assets, vulnerabilities, and security findings.
// Maintains an in-memory knowledge graph that is populated by scan results
// and can be queried by the SentinelGuard agent for decision-making.

export interface DiscoveredAsset {
  id: string;
  host: string;
  type: "server" | "workstation" | "network_device" | "service" | "unknown";
  firstSeen: string;
  lastSeen: string;
  openPorts: number[];
  services: ServiceInfo[];
  vulnerabilities: VulnerabilityRecord[];
  tags: string[];
}

export interface ServiceInfo {
  port: number;
  protocol: string;
  name: string;
  version: string;
  banner?: string;
}

export interface VulnerabilityRecord {
  id: string;
  cve?: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  title: string;
  description: string;
  affectedService: string;
  discoveredAt: string;
  status: "open" | "mitigated" | "accepted" | "false_positive";
  remediation?: string;
}

export class SecurityKnowledgeBase {
  private assets: Map<string, DiscoveredAsset> = new Map();

  /**
   * Register or update a discovered asset from scan results.
   */
  upsertAsset(host: string, data: Partial<DiscoveredAsset>): DiscoveredAsset {
    const existing = this.assets.get(host);
    const now = new Date().toISOString();

    if (existing) {
      // Merge new data into existing asset
      existing.lastSeen = now;
      if (data.openPorts) {
        existing.openPorts = [...new Set([...existing.openPorts, ...data.openPorts])];
      }
      if (data.services) {
        for (const svc of data.services) {
          const existingSvc = existing.services.find(
            (s) => s.port === svc.port && s.protocol === svc.protocol
          );
          if (!existingSvc) {
            existing.services.push(svc);
          } else {
            Object.assign(existingSvc, svc);
          }
        }
      }
      if (data.vulnerabilities) {
        existing.vulnerabilities.push(...data.vulnerabilities);
      }
      if (data.tags) {
        existing.tags = [...new Set([...existing.tags, ...data.tags])];
      }
      return existing;
    }

    const asset: DiscoveredAsset = {
      id: `asset-${host.replace(/[^a-zA-Z0-9]/g, "-")}`,
      host,
      type: data.type || "unknown",
      firstSeen: now,
      lastSeen: now,
      openPorts: data.openPorts || [],
      services: data.services || [],
      vulnerabilities: data.vulnerabilities || [],
      tags: data.tags || [],
    };

    this.assets.set(host, asset);
    return asset;
  }

  /**
   * Add a vulnerability to a specific asset.
   */
  addVulnerability(host: string, vuln: VulnerabilityRecord): void {
    const asset = this.assets.get(host);
    if (asset) {
      asset.vulnerabilities.push(vuln);
    }
  }

  /**
   * Get an asset by host identifier.
   */
  getAsset(host: string): DiscoveredAsset | undefined {
    return this.assets.get(host);
  }

  /**
   * Get all discovered assets.
   */
  getAllAssets(): DiscoveredAsset[] {
    return Array.from(this.assets.values());
  }

  /**
   * Query assets by open port.
   */
  getAssetsByPort(port: number): DiscoveredAsset[] {
    return Array.from(this.assets.values()).filter((a) =>
      a.openPorts.includes(port)
    );
  }

  /**
   * Get all assets with open vulnerabilities of a given severity or higher.
   */
  getVulnerableAssets(
    minSeverity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" = "MEDIUM"
  ): DiscoveredAsset[] {
    const severityOrder = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
    const minIndex = severityOrder.indexOf(minSeverity);

    return Array.from(this.assets.values()).filter((a) =>
      a.vulnerabilities.some(
        (v) =>
          v.status === "open" &&
          severityOrder.indexOf(v.severity) >= minIndex
      )
    );
  }

  /**
   * Get a summary of the current security posture.
   */
  getSummary(): {
    totalAssets: number;
    totalVulnerabilities: number;
    bySeverity: Record<string, number>;
    highRiskAssets: string[];
  } {
    const allVulns = Array.from(this.assets.values()).flatMap(
      (a) => a.vulnerabilities.filter((v) => v.status === "open")
    );

    const bySeverity: Record<string, number> = {
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
      INFO: 0,
    };
    for (const v of allVulns) {
      bySeverity[v.severity] = (bySeverity[v.severity] || 0) + 1;
    }

    const highRiskAssets = Array.from(this.assets.values())
      .filter((a) =>
        a.vulnerabilities.some(
          (v) =>
            v.status === "open" &&
            (v.severity === "CRITICAL" || v.severity === "HIGH")
        )
      )
      .map((a) => a.host);

    return {
      totalAssets: this.assets.size,
      totalVulnerabilities: allVulns.length,
      bySeverity,
      highRiskAssets,
    };
  }

  /**
   * Clear all data (useful for testing).
   */
  clear(): void {
    this.assets.clear();
  }
}
