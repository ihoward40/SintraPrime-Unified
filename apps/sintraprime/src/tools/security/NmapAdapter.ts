// src/tools/security/NmapAdapter.ts
// Wraps the Nmap network scanner as a first-class SintraPrime Tool.
// Requires Nmap to be installed in the execution environment.
// All scans are subject to PolicyGate approval and ReceiptLedger logging.

import { Tool } from "../../types/index.js";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface NmapScanArgs {
  target: string;           // IP, hostname, or CIDR range (e.g., "192.168.1.0/24")
  options?: string;         // Nmap flags (default: "-sV" for service version detection)
  timeout?: number;         // Scan timeout in ms (default: 300000 = 5 min)
}

export interface NmapFinding {
  host: string;
  status: string;
  openPorts: Array<{
    port: number;
    protocol: string;
    service: string;
    version: string;
    state: string;
  }>;
}

export class NmapAdapter implements Tool {
  public readonly name = "nmap_scan";
  public readonly description =
    "Performs a network scan using Nmap to discover live hosts, open ports, " +
    "running services, and OS fingerprints. Returns structured JSON findings. " +
    "Requires Nmap to be installed in the execution environment.";

  async execute(args: NmapScanArgs): Promise<{ target: string; findings: NmapFinding[]; rawXml: string }> {
    if (!args.target) {
      throw new Error("NmapAdapter: 'target' argument is required.");
    }

    // Strict input sanitization to prevent command injection.
    // Only allow alphanumeric characters, dots, hyphens, forward slashes (for CIDR), and commas.
    const sanitizedTarget = args.target.replace(/[^a-zA-Z0-9.\-/,]/g, "");
    if (!sanitizedTarget) {
      throw new Error("NmapAdapter: Invalid target after sanitization.");
    }

    // Default to service version detection; output as XML for reliable parsing.
    const options = args.options || "-sV";
    const command = `nmap ${options} -oX - ${sanitizedTarget}`;
    const timeout = args.timeout || 300000;

    let stdout: string;
    try {
      const result = await execAsync(command, { timeout });
      stdout = result.stdout;
    } catch (error: any) {
      // Nmap exits with code 1 for some warnings; still parse the output.
      if (error.stdout) {
        stdout = error.stdout as string;
      } else {
        throw new Error(`NmapAdapter: Scan failed for target '${sanitizedTarget}': ${error.message}`);
      }
    }

    // Parse the XML output into a clean JSON structure.
    const findings = this.parseNmapXml(stdout);

    return {
      target: sanitizedTarget,
      findings,
      rawXml: stdout,
    };
  }

  /**
   * Parse Nmap XML output into structured findings.
   * Uses simple regex-based parsing to avoid additional XML dependencies.
   */
  private parseNmapXml(xml: string): NmapFinding[] {
    try {
      const findings: NmapFinding[] = [];

      // Extract host blocks from XML
      const hostRegex = /<host\b[^>]*>([\s\S]*?)<\/host>/g;
      let hostMatch: RegExpExecArray | null;

      while ((hostMatch = hostRegex.exec(xml)) !== null) {
        const hostBlock = hostMatch[1] ?? "";

        // Extract address
        const addrMatch = hostBlock.match(/<address\s+addr="([^"]+)"/);
        const address = addrMatch?.[1] ?? "unknown";

        // Extract status
        const statusMatch = hostBlock.match(/<status\s+state="([^"]+)"/);
        const status = statusMatch?.[1] ?? "unknown";

        // Extract ports
        const portRegex = /<port\s+protocol="([^"]+)"\s+portid="(\d+)">([\s\S]*?)<\/port>/g;
        let portMatch: RegExpExecArray | null;
        const openPorts: NmapFinding["openPorts"] = [];

        while ((portMatch = portRegex.exec(hostBlock)) !== null) {
          const protocol = portMatch[1] ?? "";
          const portId = parseInt(portMatch[2] ?? "0", 10);
          const portBlock = portMatch[3] ?? "";

          // Check state
          const stateMatch = portBlock.match(/<state\s+state="([^"]+)"/);
          const state = stateMatch?.[1] ?? "unknown";

          if (state === "open") {
            // Extract service info
            const serviceMatch = portBlock.match(/<service\s+name="([^"]*)"(?:\s+product="([^"]*)")?(?:\s+version="([^"]*)")?/);
            const serviceName = serviceMatch?.[1] ?? "unknown";
            const product = serviceMatch?.[2] ?? "";
            const version = serviceMatch?.[3] ?? "";

            openPorts.push({
              port: portId,
              protocol,
              service: serviceName,
              version: `${product} ${version}`.trim(),
              state,
            });
          }
        }

        findings.push({ host: address, status, openPorts });
      }

      return findings;
    } catch {
      // If parsing fails, return empty findings rather than crashing.
      return [];
    }
  }
}
