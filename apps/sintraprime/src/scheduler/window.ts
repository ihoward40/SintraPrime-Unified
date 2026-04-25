import crypto from "node:crypto";
import rrule from "rrule";

const RRule = (rrule as any).RRule;

function ruleFromStringDeterministic(rruleStr: string) {
  const opts = RRule.parseString(rruleStr);
  const dtstart = new Date(Date.UTC(1970, 0, 1, 0, 0, 0));
  return new RRule({ ...opts, dtstart });
}

export function computeWindowId(job_id: string, rruleStr: string, now: Date): string {
  const rule = ruleFromStringDeterministic(rruleStr);
  const windowStart: Date | null = rule.before(now, true);
  if (!windowStart) return "never";

  const key = `${job_id}:${windowStart.toISOString()}`;
  return crypto.createHash("sha256").update(key).digest("hex").slice(0, 16);
}
