export type GuardOp = "==" | "!=";

export type StepGuard = {
  path: string;
  op: GuardOp;
  value: any;
};

function getByPath(snapshot: any, rawPath: string): any {
  const path = String(rawPath ?? "").replace(/^\$/, "").trim();
  if (!path) return undefined;

  const parts = path.split(".");
  let cur: any = snapshot;

  for (const part of parts) {
    if (cur === null || cur === undefined) return undefined;

    // Handle array indexing segments like rich_text[0]
    if (part.includes("[")) {
      const m = part.match(/^([^\[]+)\[(\d+)\]$/);
      if (!m) return undefined;
      const key = String(m[1] ?? "");
      if (!key) return undefined;
      const idx = Number(m[2]);
      cur = cur?.[key];
      if (!Array.isArray(cur)) return undefined;
      cur = cur[idx];
      continue;
    }

    cur = cur?.[part];
  }

  return cur;
}

export function evaluateGuards(
  snapshot: any,
  guards: StepGuard[]
): { ok: boolean; failed?: any } {
  for (const g of guards) {
    const actual = getByPath(snapshot, g.path);
    const pass = g.op === "==" ? actual === g.value : actual !== g.value;

    if (!pass) {
      return { ok: false, failed: { ...g, actual } };
    }
  }

  return { ok: true };
}
