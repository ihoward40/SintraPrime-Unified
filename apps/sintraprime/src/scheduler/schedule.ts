import rrule from "rrule";

const RRule = (rrule as any).RRule;

function ruleFromStringDeterministic(rruleStr: string) {
  // IMPORTANT: RRule.fromString defaults dtstart to "now".
  // That makes rule.before(at) return null for historical timestamps.
  // We pin dtstart so schedule evaluation is stable for any --at.
  const opts = RRule.parseString(rruleStr);
  const dtstart = new Date(Date.UTC(1970, 0, 1, 0, 0, 0));
  return new RRule({ ...opts, dtstart });
}

export function shouldRunAt(rruleStr: string, at: Date): boolean {
  const rule = ruleFromStringDeterministic(rruleStr);
  const last = rule.before(at, true);
  return !!last && Math.abs(at.getTime() - last.getTime()) < 60_000;
}

export function nextEligibleAt(rruleStr: string, at: Date): Date | null {
  const rule = ruleFromStringDeterministic(rruleStr);
  return rule.after(at, false) ?? null;
}

export function shouldRunNow(rruleStr: string): boolean {
  return shouldRunAt(rruleStr, new Date());
}

export function nowUtcIso() {
  return new Date().toISOString();
}
