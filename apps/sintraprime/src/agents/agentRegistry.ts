import fs from "node:fs";
import path from "node:path";

export type AgentEntry = {
  name: string;
  version: string;
  capabilities: string[];
};

export type AgentRegistry = {
  agents: AgentEntry[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function parseAgentEntry(value: unknown): AgentEntry {
  if (!isRecord(value)) throw new Error("agents/registry.json agents[] entries must be objects");
  const name = value.name;
  const version = value.version;
  const capabilities = value.capabilities;
  if (typeof name !== "string" || !name.trim()) throw new Error("agents/registry.json agent entry missing name");
  if (typeof version !== "string" || !version.trim()) throw new Error(`agents/registry.json agent '${name}' missing version`);
  if (!Array.isArray(capabilities) || !capabilities.every((c) => typeof c === "string")) {
    throw new Error(`agents/registry.json agent '${name}' capabilities must be string[]`);
  }
  return { name, version, capabilities };
}

function toAgentRegistryFromLegacy(parsed: Record<string, unknown>): AgentRegistry {
  // Backward compatibility with Tier-4 registry shape:
  // { validator: { current: "1.2.0" }, planner: { current: "1.1.3" } }
  const validator = parsed.validator;
  const planner = parsed.planner;
  if (!isRecord(validator) || typeof validator.current !== "string") {
    throw new Error("agents/registry.json missing validator.current");
  }
  if (!isRecord(planner) || typeof planner.current !== "string") {
    throw new Error("agents/registry.json missing planner.current");
  }

  return {
    agents: [
      { name: "validation-agent", version: validator.current, capabilities: ["command.validate"] },
      { name: "planner-agent", version: planner.current, capabilities: ["plan.generate"] },
    ],
  };
}

export function loadAgentRegistry(): AgentRegistry {
  const file = path.join(process.cwd(), "agents", "registry.json");
  const raw = fs.readFileSync(file, "utf8");
  const parsed = JSON.parse(raw);

  if (!isRecord(parsed)) throw new Error("agents/registry.json must be an object");

  if (Array.isArray(parsed.agents)) {
    const agents = parsed.agents.map(parseAgentEntry);
    if (!agents.length) throw new Error("agents/registry.json agents[] must not be empty");
    return { agents };
  }

  return toAgentRegistryFromLegacy(parsed);
}

export function findAgentsProvidingCapability(registry: AgentRegistry, capability: string): AgentEntry[] {
  return registry.agents.filter((a) => a.capabilities.includes(capability));
}

export function formatAgentRef(agent: AgentEntry): string {
  return `${agent.name}@${agent.version}`;
}
