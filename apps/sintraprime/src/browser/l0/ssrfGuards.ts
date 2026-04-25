import { URL } from "node:url";
import net from "node:net";

export type BrowserL0GuardCode =
  | "BAD_URL"
  | "SCHEME_NOT_ALLOWED"
  | "HOST_NOT_ALLOWED"
  | "SSRF_GUARD_BLOCKED";

export class BrowserL0GuardError extends Error {
  code: BrowserL0GuardCode;

  constructor(code: BrowserL0GuardCode, message: string) {
    super(message);
    this.code = code;
  }
}

const DENY_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function isIPv4Literal(host: string): boolean {
  return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host);
}

function isPrivateOrLocalIPv4(ip: string): boolean {
  const parts = ip.split(".").map((n) => parseInt(n, 10));
  if (parts.length !== 4) return false;
  if (parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return false;
  const a = parts[0]!;
  const b = parts[1] ?? -1;

  // 0.0.0.0/8, 10/8, 127/8, 169.254/16, 172.16/12, 192.168/16, 100.64/10
  if (a === 0) return true;
  if (a === 10) return true;
  if (a === 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  return false;
}

function hostMatchesPattern(host: string, pattern: string): boolean {
  const p = pattern.toLowerCase();
  if (p === host) return true;
  if (p.startsWith("*.")) {
    const root = p.slice(2);
    if (!root) return false;
    return host === root || host.endsWith(`.${root}`);
  }
  return false;
}

export function assertUrlSafeForL0(
  rawUrl: string,
  opts?: {
    allowedSchemes?: string[]; // e.g. ["https:", "data:"]
    allowedHosts?: string[]; // e.g. ["example.com", "*.example.com"]
    requireAllowedHosts?: boolean; // default true
  }
) {
  let u: URL;
  try {
    u = new URL(rawUrl);
  } catch {
    throw new BrowserL0GuardError("BAD_URL", `invalid url: ${rawUrl}`);
  }

  const allowedSchemes = (opts?.allowedSchemes ?? ["https:"]).map((s) => s.toLowerCase());
  const protocol = u.protocol.toLowerCase();
  if (!allowedSchemes.includes(protocol)) {
    throw new BrowserL0GuardError("SCHEME_NOT_ALLOWED", `scheme not allowed: ${u.protocol}`);
  }

  // data: has no hostname; allow if scheme allowlisted.
  if (protocol === "data:") return;

  // Explicitly block bracketed hosts like http://[::1]/
  // Note: rely on URL parsing (host/hostname), not raw string scanning.
  if (u.host.includes("[") || u.host.includes("]")) {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `bracketed host blocked: ${u.host}`);
  }

  const host = u.hostname.toLowerCase();
  if (DENY_HOSTS.has(host) || host.endsWith(".local")) {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `host denylisted: ${host}`);
  }

  // Block known cloud metadata SSRF target (even if allowlisted by mistake).
  if (host === "169.254.169.254") {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `blocked metadata host: ${host}`);
  }

  // Conservative: no IPv6 literals for L0.
  if (host.includes(":")) {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `IPv6/IP-literal blocked: ${host}`);
  }

  const ipKind = net.isIP(host);
  if (ipKind === 6) {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `IPv6 literal blocked: ${host}`);
  }

  if (isIPv4Literal(host) && isPrivateOrLocalIPv4(host)) {
    throw new BrowserL0GuardError("SSRF_GUARD_BLOCKED", `private/local IPv4 blocked: ${host}`);
  }

  const requireAllowedHosts = opts?.requireAllowedHosts ?? true;
  if (requireAllowedHosts) {
    const allowedHosts = (opts?.allowedHosts ?? []).map((h) => String(h).trim()).filter(Boolean);
    if (!allowedHosts.length) {
      throw new BrowserL0GuardError("HOST_NOT_ALLOWED", "allowed host list is empty (deny-by-default)");
    }
    const ok = allowedHosts.some((pat) => hostMatchesPattern(host, pat));
    if (!ok) {
      throw new BrowserL0GuardError("HOST_NOT_ALLOWED", `host not allowlisted: ${host}`);
    }
  }
}
