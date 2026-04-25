import { Tool } from "../../types/index.js";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface HydraRunArgs {
  target: string; // Target service URL (e.g., "ftp://192.168.1.1")
  userList: string; // Path to user list file
  passwordList: string; // Path to password list file
  options?: string; // Additional Hydra options
}

export class HydraAdapter implements Tool {
  public readonly name = "hydra_run";
  public readonly description = "HIGH-RISK: Performs an online password cracking attack using Hydra. REQUIRES explicit human approval.";

  async execute(args: HydraRunArgs): Promise<any> {
    const { target, userList, passwordList, options } = args;
    if (!target || !userList || !passwordList) {
      throw new Error("HydraAdapter: 'target', 'userList', and 'passwordList' are required.");
    }

    const command = `hydra -L ${userList} -P ${passwordList} ${target} ${options || ''}`;

    try {
      const { stdout } = await execAsync(command, { timeout: 1800000 }); // 30-minute timeout
      return { target, found: stdout };
    } catch (error: any) {
      // Hydra exits with non-zero code if no passwords are found, so check output
      if (error.stdout) {
        return { target, found: error.stdout };
      }
      console.error(`HydraAdapter: Execution failed for target ${target}`, error);
      throw new Error(`Hydra failed: ${error.message}`);
    }
  }
}
