// src/tools/security/MetasploitAdapter.ts
// Interfaces with the Metasploit Framework via its RPC API (msfrpcd).
// Requires Metasploit Framework to be running with the RPC daemon enabled.
// CRITICAL: This tool must ONLY be used against authorized targets.
// The PolicyGate MUST require explicit human approval before any call to this tool.

import { Tool } from "../../types/index.js";
import * as http from "http";

export interface MetasploitExploitArgs {
  module: string;          // e.g., "exploit/unix/ftp/vsftpd_234_backdoor"
  rhosts: string;          // Target host(s)
  rport?: number;          // Target port
  payload?: string;        // e.g., "cmd/unix/interact"
  additionalOptions?: Record<string, string>;
}

export interface MetasploitRpcResponse {
  result?: string;
  token?: string;
  id?: string;
  data?: string;
  error?: boolean;
  error_message?: string;
}

export class MetasploitAdapter implements Tool {
  public readonly name = "metasploit_exploit";
  public readonly description =
    "Executes a Metasploit exploit module against a specified target. " +
    "REQUIRES explicit human approval from the PolicyGate before execution. " +
    "Must ONLY be used against systems for which written authorization has been obtained.";

  private rpcHost: string;
  private rpcPort: number;
  private authToken: string | null = null;
  private rpcPassword: string;

  constructor(config?: { host?: string; port?: number; password?: string }) {
    this.rpcHost = config?.host || process.env.METASPLOIT_RPC_HOST || "127.0.0.1";
    this.rpcPort = config?.port || parseInt(process.env.METASPLOIT_RPC_PORT || "55553", 10);
    this.rpcPassword = config?.password || process.env.METASPLOIT_RPC_PASSWORD || "";
  }

  /**
   * Send a JSON-RPC request to the Metasploit RPC daemon.
   */
  private async rpcCall(method: string, params: Record<string, any> = {}): Promise<MetasploitRpcResponse> {
    const body = JSON.stringify({ method, ...params });

    return new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: this.rpcHost,
          port: this.rpcPort,
          path: "/api/",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let data = "";
          res.on("data", (chunk) => (data += chunk));
          res.on("end", () => {
            try {
              resolve(JSON.parse(data));
            } catch {
              reject(new Error(`MetasploitAdapter: Invalid JSON response: ${data}`));
            }
          });
        }
      );

      req.on("error", (err) => reject(new Error(`MetasploitAdapter: RPC connection failed: ${err.message}`)));
      req.setTimeout(30000, () => {
        req.destroy();
        reject(new Error("MetasploitAdapter: RPC request timed out."));
      });
      req.write(body);
      req.end();
    });
  }

  /**
   * Authenticate with the Metasploit RPC daemon.
   */
  private async authenticate(): Promise<void> {
    if (this.authToken) return;

    if (!this.rpcPassword) {
      throw new Error("MetasploitAdapter: METASPLOIT_RPC_PASSWORD is not configured.");
    }

    try {
      const response = await this.rpcCall("auth.login", {
        username: "msf",
        password: this.rpcPassword,
      });

      if (response.error) {
        throw new Error(response.error_message || "Authentication failed");
      }

      this.authToken = response.token || null;
      if (!this.authToken) {
        throw new Error("No token received from Metasploit RPC.");
      }
    } catch (error: any) {
      console.error("MetasploitAdapter: Authentication failed.", error.message);
      throw error;
    }
  }

  async execute(args: MetasploitExploitArgs): Promise<any> {
    // Authenticate if not already
    await this.authenticate();

    if (!this.authToken) {
      throw new Error("MetasploitAdapter: Not authenticated to Metasploit RPC.");
    }
    if (!args.module || !args.rhosts) {
      throw new Error("MetasploitAdapter: 'module' and 'rhosts' are required.");
    }

    // Sanitize inputs
    const sanitizedModule = args.module.replace(/[^a-zA-Z0-9/_\-]/g, "");
    const sanitizedRhosts = args.rhosts.replace(/[^a-zA-Z0-9.\-/,]/g, "");

    // 1. Create a new console session.
    const consoleResponse = await this.rpcCall("console.create", {
      token: this.authToken,
    });
    const consoleId = consoleResponse.id;

    if (!consoleId) {
      throw new Error("MetasploitAdapter: Failed to create console session.");
    }

    // 2. Build and execute the exploit command.
    const commands = [
      `use ${sanitizedModule}`,
      `set RHOSTS ${sanitizedRhosts}`,
      args.rport ? `set RPORT ${args.rport}` : "",
      args.payload ? `set PAYLOAD ${args.payload}` : "",
      ...Object.entries(args.additionalOptions || {}).map(
        ([k, v]) => `set ${k.replace(/[^a-zA-Z0-9_]/g, "")} ${v}`
      ),
      "run -z",
    ]
      .filter(Boolean)
      .join("\n");

    await this.rpcCall("console.write", {
      token: this.authToken,
      id: consoleId,
      data: commands + "\n",
    });

    // 3. Poll for output (simplified; a real implementation would poll until done).
    await new Promise((resolve) => setTimeout(resolve, 10000));
    const outputResponse = await this.rpcCall("console.read", {
      token: this.authToken,
      id: consoleId,
    });

    // 4. Destroy the console session.
    await this.rpcCall("console.destroy", {
      token: this.authToken,
      id: consoleId,
    });

    return {
      module: sanitizedModule,
      target: sanitizedRhosts,
      output: outputResponse.data || "",
    };
  }
}
