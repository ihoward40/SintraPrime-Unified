export function nowMs(): number {
  const fixed = process.env.SMOKE_FIXED_NOW_ISO;
  if (typeof fixed === "string" && fixed.trim()) {
    const t = new Date(fixed).getTime();
    if (Number.isFinite(t)) return t;
  }
  return Date.now();
}

export function nowIso(): string {
  return new Date(nowMs()).toISOString();
}
