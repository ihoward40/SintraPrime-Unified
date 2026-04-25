import crypto from "node:crypto";

function sha256(text: string) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

export function normalizePromotionCommand(command: string) {
  return String(command ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

export function normalizeCapabilitySet(requiredCapabilities: string[]) {
  const uniq = Array.from(new Set(requiredCapabilities.map((c) => String(c ?? "").trim()).filter(Boolean)));
  uniq.sort();
  return uniq;
}

export function normalizeAdapterType(adapterType: string) {
  return String(adapterType ?? "").trim() || "unknown";
}

export function computePromotionFingerprint(args: {
  command: string;
  capability_set: string[];
  adapter_type: string;
}) {
  const payload = {
    normalized_command: normalizePromotionCommand(args.command),
    capability_set: normalizeCapabilitySet(args.capability_set),
    adapter_type: normalizeAdapterType(args.adapter_type),
  };

  const canonical = JSON.stringify(payload);
  return `auto_${sha256(canonical).slice(0, 16)}`;
}
