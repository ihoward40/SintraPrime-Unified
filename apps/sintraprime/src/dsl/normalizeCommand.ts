function tokenizeCommand(input: string): string[] {
  const tokens: string[] = [];
  let cur = "";
  let quote: "'" | '"' | null = null;

  const push = () => {
    const t = cur.trim();
    if (t) tokens.push(t);
    cur = "";
  };

  for (let i = 0; i < input.length; i++) {
    const ch = input[i];

    if (quote) {
      if (ch === "\\" && i + 1 < input.length) {
        // Basic escaping inside quotes.
        cur += input[i + 1];
        i++;
        continue;
      }
      if (ch === quote) {
        quote = null;
        continue;
      }
      cur += ch;
      continue;
    }

    if (ch === '"' || ch === "'") {
      quote = ch;
      continue;
    }

    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      push();
      continue;
    }

    cur += ch;
  }

  push();
  return tokens;
}

function toJsonArgString(obj: Record<string, unknown>) {
  return JSON.stringify(obj);
}

export function normalizeCommand(raw: string): string {
  const original = String(raw ?? "").trim();
  if (!original) return original;

  // Tier-10.4: conditional guards
  // Syntax: --if Field!=Value
  let s = original;
  const guardMatch = s.match(/--if\s+(.+)$/i);
  let guard: null | { field: string; op: "!=" | "=="; value: string } = null;
  if (guardMatch) {
    const expr = String(guardMatch[1] ?? "").trim();
    const m2 = expr.match(/^(\w+)\s*(!=|==)\s*(.+)$/);
    if (m2) {
      const field = String(m2[1] ?? "");
      const op = m2[2] === "==" ? "==" : "!=";
      const value = String(m2[3] ?? "");
      if (field && value) {
        guard = { field, op, value };
      }
      s = s.replace(/--if\s+.+$/i, "").trim();
    }
  }

  const tokens = tokenizeCommand(s);
  if (tokens.length === 0) return original;

  // DSL sugar: /intake <path>
  // Canonical form: /build document-intake {"path":"./docs"}
  if (tokens[0] === "/intake") {
    // Must fully recognize syntax: exactly one positional argument.
    if (tokens.length !== 2) return original;
    const path = tokens[1];
    if (!path || !path.trim()) return original;
    return `/build document-intake ${toJsonArgString({ path })}`;
  }

  // Tier-10.3: /notion live set <page_id> k=v k=v ...
  // Rewrites into canonical JSON args after the command, preserving transport contract.
  if (tokens[0] === "/notion" && tokens[1] === "live" && tokens[2] === "set") {
    if (tokens.length < 5) return original;
    const pageId = tokens[3];
    if (!pageId || !pageId.trim()) return original;

    // If args already look like inline JSON, leave as-is.
    const tailFirst = tokens[4];
    if (typeof tailFirst === "string" && tailFirst.trim().startsWith("{")) {
      return original;
    }

    const props: Record<string, string> = {};
    for (const p of tokens.slice(4)) {
      const ix = p.indexOf("=");
      if (ix > 0) {
        const k = p.slice(0, ix).trim();
        const v = p.slice(ix + 1).trim();
        if (k && v) props[k] = v;
      }
    }

    if (Object.keys(props).length === 0) return original;
    return `/notion live set ${pageId} ${toJsonArgString({
      properties: props,
      guards: guard ? [guard] : [],
    })}`;
  }

  return original;
}
