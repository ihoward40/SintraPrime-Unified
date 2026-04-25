import { Tool } from "../../types/index.js";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface SqlmapRunArgs {
  url: string; // Target URL to test
  options?: string; // Additional sqlmap command-line options (e.g., '--dbs', '--level=5')
}

export class SqlmapAdapter implements Tool {
  public readonly name = "sqlmap_run";
  public readonly description = "HIGH-RISK: Runs sqlmap to test for SQL injection vulnerabilities. REQUIRES explicit human approval.";

  async execute(args: SqlmapRunArgs): Promise<any> {
    if (!args.url) {
      throw new Error("SqlmapAdapter: 'url' argument is required.");
    }

    // Use --batch to run non-interactively
    const command = `sqlmap -u "${args.url}" --batch ${args.options || ''}`;

    try {
      const { stdout } = await execAsync(command, { timeout: 600000 }); // 10-minute timeout
      return { target: args.url, output: stdout };
    } catch (error: any) {
      console.error(`SqlmapAdapter: Execution failed for URL ${args.url}`, error);
      // Even on error, return output as it may contain partial findings
      return { target: args.url, output: error.stdout || error.message };
    }
  }
}
