// src/tools/security/OsintTool.ts
// Performs Open-Source Intelligence (OSINT) gathering using theHarvester and Amass.
// These tools must be installed in the execution environment.

import { Tool } from "../../types/index.js";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface OsintGatherArgs {
  domain: string;          // Target domain (e.g., "example.com")
  sources?: string[];      // theHarvester sources (e.g., ["google", "bing", "linkedin"])
  runAmass?: boolean;      // Whether to also run Amass for subdomain enumeration
}

export interface OsintResult {
  domain: string;
  emails: string[];
  subdomains: string[];
  hosts: string[];
  ips: string[];
}

export class OsintTool implements Tool {
  public readonly name = "osint_gather";
  public readonly description =
    "Performs passive OSINT gathering on a target domain using theHarvester " +
    "and Amass. Discovers email addresses, subdomains, employee names, and " +
    "associated IP addresses from public sources without active probing.";

  async execute(args: OsintGatherArgs): Promise<OsintResult> {
    if (!args.domain) {
      throw new Error("OsintTool: 'domain' argument is required.");
    }

    // Sanitize domain input.
    const sanitizedDomain = args.domain.replace(/[^a-zA-Z0-9.\-]/g, "");
    if (!sanitizedDomain) {
      throw new Error("OsintTool: Invalid domain after sanitization.");
    }

    const result: OsintResult = {
      domain: sanitizedDomain,
      emails: [],
      subdomains: [],
      hosts: [],
      ips: [],
    };

    // Run theHarvester
    const sources = (args.sources || ["google", "bing"]).join(",");
    const harvesterCommand = `theHarvester -d ${sanitizedDomain} -b ${sources} -f /tmp/harvester_output`;
    try {
      await execAsync(harvesterCommand, { timeout: 120000 });
      // Parse the JSON output file written by theHarvester.
      const { stdout: fileContent } = await execAsync(
        `cat /tmp/harvester_output.json 2>/dev/null || echo "{}"`
      );
      const parsed = JSON.parse(fileContent || "{}");
      result.emails = parsed.emails || [];
      result.hosts = parsed.hosts || [];
      result.ips = parsed.ips || [];
    } catch (error: any) {
      console.warn(`OsintTool: theHarvester encountered an issue: ${error.message}`);
    }

    // Optionally run Amass for subdomain enumeration
    if (args.runAmass !== false) {
      const amassCommand = `amass enum -passive -d ${sanitizedDomain} -o /tmp/amass_output.txt`;
      try {
        await execAsync(amassCommand, { timeout: 180000 });
        const { stdout: amassOutput } = await execAsync(
          `cat /tmp/amass_output.txt 2>/dev/null || echo ""`
        );
        const subdomains = amassOutput.split("\n").filter(Boolean);
        result.subdomains = [...new Set([...result.subdomains, ...subdomains])];
      } catch (error: any) {
        console.warn(`OsintTool: Amass encountered an issue: ${error.message}`);
      }
    }

    return result;
  }
}
