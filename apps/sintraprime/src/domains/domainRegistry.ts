import fs from "node:fs";
import path from "node:path";

export type DomainOverlay = {
  // Tier-21 MVP: overlay can tighten policy; never loosen.
  deny_write?: boolean;
};

export type DomainRegistryEntry = {
  domain_id: string;
  description?: string;
  overlay?: DomainOverlay;
};

export type DomainRegistry = {
  kind: "TrustDomainRegistry";
  generated_at: string;
  domains: Record<string, DomainRegistryEntry>;
};

function registryPath() {
  return path.join(process.cwd(), "runs", "domains", "registry.json");
}

export function readDomainRegistry(): DomainRegistry | null {
  try {
    const p = registryPath();
    if (!fs.existsSync(p)) return null;
    const json = JSON.parse(fs.readFileSync(p, "utf8"));
    return json as DomainRegistry;
  } catch {
    return null;
  }
}

export function readDomainOverlay(domain_id: string | null | undefined): DomainOverlay | null {
  const did = typeof domain_id === "string" ? domain_id.trim() : "";
  if (!did) return null;

  const reg = readDomainRegistry();
  const entry = reg?.domains?.[did];
  if (!entry || typeof entry !== "object") return null;

  const overlay = (entry as any).overlay;
  if (!overlay || typeof overlay !== "object") return null;

  return overlay as DomainOverlay;
}
