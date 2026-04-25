import crypto from "node:crypto";

export function stableStringify(value: unknown): string {
  const stable = (v: any): any => {
    if (v === null || v === undefined) return v;
    if (Array.isArray(v)) return v.map(stable);
    if (typeof v !== "object") return v;
    const keys = Object.keys(v).sort();
    const out: any = {};
    for (const k of keys) out[k] = stable(v[k]);
    return out;
  };

  return JSON.stringify(stable(value));
}

export function sha256HexUtf8(text: string): string {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

export function sha256HexStableJson(value: unknown): string {
  return sha256HexUtf8(stableStringify(value));
}
