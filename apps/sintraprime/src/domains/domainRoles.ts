import fs from "node:fs";
import path from "node:path";

export type DomainRole = "approver" | "viewer" | "operator";

export type OperatorDomainRoleAssignment = {
  roles: DomainRole[];
};

export type OperatorRolesFile = {
  operator_id: string;
  assigned_at: string;
  domains: Record<string, OperatorDomainRoleAssignment>;
};

function rolesPath(operator_id: string) {
  return path.join(process.cwd(), "runs", "domains", "roles", `${operator_id}.json`);
}

export function readOperatorRoles(operator_id: string): OperatorRolesFile | null {
  try {
    const p = rolesPath(operator_id);
    if (!fs.existsSync(p)) return null;
    const json = JSON.parse(fs.readFileSync(p, "utf8"));
    return json as OperatorRolesFile;
  } catch {
    return null;
  }
}

export function operatorHasRole(params: {
  operator_id: string;
  domain_id: string;
  role: DomainRole;
}): boolean {
  const operator_id = String(params.operator_id ?? "").trim();
  const domain_id = String(params.domain_id ?? "").trim();
  const role = params.role;

  if (!operator_id || !domain_id) return false;

  const rolesFile = readOperatorRoles(operator_id);
  const assigned = rolesFile?.domains?.[domain_id];
  const roles = Array.isArray((assigned as any)?.roles) ? ((assigned as any).roles as unknown[]) : [];

  return roles.some((r) => String(r).trim() === role);
}

export function getOperatorId(env: NodeJS.ProcessEnv = process.env): string {
  const fromEnv = String(env.OPERATOR_ID ?? "").trim();
  if (fromEnv) return fromEnv;

  const fromUser = String(env.USER ?? env.USERNAME ?? "").trim();
  if (fromUser) return fromUser;

  return "operator@local";
}
