import { sendMessage } from "../agents/sendMessage.js";
import { enforceMaxRunsPerDay } from "../autonomy/budget.js";
import { writeAutonomySummary } from "../artifacts/writeAutonomySummary.js";
import { nowIso as fixedNowIso } from "../utils/clock.js";
import { enforceCliCredits } from "../credits/enforceCliCredits.js";

const mode = String(process.env.AUTONOMY_MODE || "OFF");

function nowIso() {
  return new Date().toISOString();
}

async function main() {
  if (mode === "OFF") {
    console.error("[AUTONOMY] mode=OFF (no-op)");
    process.exit(0);
  }

  const deny = enforceMaxRunsPerDay();
  if (deny) {
    console.log(JSON.stringify(deny));
    process.exit(3);
  }

  const command = process.argv.slice(2).join(" ").trim();
  if (!command) {
    console.error("[AUTONOMY] missing command string");
    process.exit(2);
  }

  const threadId = (process.env.THREAD_ID || "autonomy_001").trim();

  {
    const now_iso = fixedNowIso();
    const denied = enforceCliCredits({ now_iso, threadId, command, domain_id: null });
    if (denied) {
      process.stdout.write(JSON.stringify(denied, null, 0));
      process.exit(1);
    }
  }

  const started_at = nowIso();

  const resp = await sendMessage({
    message: command,
    threadId,
    type: "user_message",
  });

  // No silent work: always produce at least one artifact.
  const execution_id =
    resp?.response?.execution_id || resp?.response?.executionId || `autonomy_${Date.now()}`;

  writeAutonomySummary({
    execution_id,
    mode,
    steps_executed: [],
    started_at,
    finished_at: nowIso(),
  });

  console.log(JSON.stringify(resp.response));
}

main().catch((e) => {
  console.error("[AUTONOMY] fatal", e);
  process.exit(1);
});
