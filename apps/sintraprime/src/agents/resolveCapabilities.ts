import type { AgentRegistry } from "./agentRegistry.js";
import { findAgentsProvidingCapability, formatAgentRef } from "./agentRegistry.js";

export type ResolvedCapability = {
  agent: string;
  version: string;
};

export type ResolvedCapabilityMap = Record<string, ResolvedCapability>;

function normalizeVersion(version: string): string {
  // Accept either "1.2.3" or "agent-name@1.2.3" (future-proof).
  const s = String(version ?? "").trim();
  if (!s) return s;
  const idx = s.lastIndexOf("@");
  return idx >= 0 ? s.slice(idx + 1) : s;
}

export function resolveCapabilities(params: {
  requiredCapabilities: string[];
  registry: AgentRegistry;
}): ResolvedCapabilityMap {
  const out: ResolvedCapabilityMap = {};

  for (const cap of params.requiredCapabilities) {
    const matches = findAgentsProvidingCapability(params.registry, cap);

    if (matches.length === 0) {
      throw new Error(`capability '${cap}' not found in agents/registry.json`);
    }
    if (matches.length > 1) {
      throw new Error(
        `capability '${cap}' is ambiguous (matches: ${matches.map((m) => formatAgentRef(m)).join(", ")})`
      );
    }

    const agent = matches[0]!;
    out[cap] = {
      agent: agent.name,
      version: normalizeVersion(agent.version),
    };
  }

  return out;
}

export function resolvedCapabilitiesToReceiptMap(resolved: ResolvedCapabilityMap): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [cap, v] of Object.entries(resolved)) {
    out[cap] = `${v.agent}@${v.version}`;
  }
  return out;
}
