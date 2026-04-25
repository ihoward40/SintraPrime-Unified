type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

const SECRET_KEYS = new Set([
  "authorization",
  "Authorization",
  "token",
  "access_token",
  "refresh_token",
  "api_key",
  "secret",
  "WEBHOOK_SECRET",
  "X-Webhook-Secret",
  "NOTION_TOKEN",
]);

function isObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function redactString(value: string): string {
  // Deterministic PII masking (lightweight; extend later).
  // SSN-like patterns.
  return value.replace(/\b\d{3}-\d{2}-\d{4}\b/g, "***-**-****");
}

export function redactJson(input: unknown): JsonValue {
  if (input === null) return null;
  if (typeof input === "boolean" || typeof input === "number") return input;
  if (typeof input === "string") return redactString(input);

  if (Array.isArray(input)) {
    return input.map((v) => redactJson(v));
  }

  if (!isObject(input)) return null;

  const out: Record<string, JsonValue> = {};
  for (const [k, v] of Object.entries(input)) {
    if (SECRET_KEYS.has(k)) {
      out[k] = "[REDACTED]";
      continue;
    }
    out[k] = redactJson(v);
  }
  return out;
}
