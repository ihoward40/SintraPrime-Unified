import { redactJson } from "../audit/redact.js";

export type NotionConfig = { token: string; base: string; version: string };
export function notionPath(path: string, write = false): string {
  const pattern = write ? /^\/v1\/pages\/[A-Za-z0-9-]+$/ : /^(?:\/v1\/(?:pages|databases)\/[A-Za-z0-9-]+|\/v1\/users\/me)$/;
  if (typeof path !== "string" || !pattern.test(path)) throw new Error("Invalid Notion path");
  return path;
}
export function notionConfig(): NotionConfig {
  const token = process.env.NOTION_TOKEN?.trim();
  if (!token) throw new Error("NOTION_TOKEN is required");
  const base = process.env.NOTION_API_BASE?.trim() || "https://api.notion.com";
  if (base !== "https://api.notion.com") throw new Error("Invalid Notion API base");
  const version = process.env.NOTION_API_VERSION?.trim() || "2022-06-28";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(version)) throw new Error("Invalid Notion API version");
  return { token, base, version };
}
export function redactNotion(value: unknown, token = notionConfig().token): ReturnType<typeof redactJson> {
  function removeToken(v: unknown): unknown {
    if (typeof v === "string") return v.split(token).join("[REDACTED]");
    if (Array.isArray(v)) return v.map(removeToken);
    if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k.split(token).join("[REDACTED]"), removeToken(x)]));
    return v;
  }
  return redactJson(removeToken(value));
}
// Read transport deliberately cannot accept an arbitrary HTTP method or body.
export async function notionLiveGet(path: string) {
  const config = notionConfig();
  const safePath = notionPath(path);
  try {
    const res = await fetch(config.base + safePath, {
      method: "GET", redirect: "error", signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${config.token}`, "Notion-Version": config.version, "Content-Type": "application/json" },
    });
    const text = await res.text();
    let value: unknown;
    try { value = JSON.parse(text); } catch { value = null; }
    if (res.status >= 200 && res.status < 300 && (!value || typeof value !== "object" || Array.isArray(value))) throw new Error("Invalid Notion response");
    return { http_status: res.status, redacted: redactNotion(value, config.token) };
  } catch { throw new Error("Notion read request failed"); }
}
export async function notionLiveWhoAmI() {
  const r = await notionLiveGet("/v1/users/me");
  return { ok: r.http_status >= 200 && r.http_status < 300, me: r.redacted };
}
