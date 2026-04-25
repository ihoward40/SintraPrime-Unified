import http from "node:http";
import path from "node:path";
import fs from "node:fs";
import fsPromises from "node:fs/promises";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

type UiCliRunResult = {
  exitCode: number;
  stdout: string;
  stderr: string;
  json: unknown | null;
};

function runEngineCliForUi(command: string): UiCliRunResult {
  const trimmed = String(command ?? "").trim();

  const entry = /^(\/queue\b|\/run\b)/i.test(trimmed)
    ? path.join(process.cwd(), "src", "cli", "run-console.ts")
    : /^\/scheduler\b/i.test(trimmed)
      ? path.join(process.cwd(), "src", "cli", "run-scheduler.ts")
      : /^\/policy\b/i.test(trimmed)
        ? path.join(process.cwd(), "src", "cli", "run-policy.ts")
        : /^\/delegate\b/i.test(trimmed)
          ? path.join(process.cwd(), "src", "cli", "run-delegate.ts")
          : /^\/operator-ui\b/i.test(trimmed)
            ? path.join(process.cwd(), "src", "cli", "run-operator-ui.ts")
            : /^\/operator\b/i.test(trimmed)
              ? path.join(process.cwd(), "src", "cli", "run-operator.ts")
              : path.join(process.cwd(), "src", "cli", "run-command.ts");

  const tsxNodeEntrypoint = path.join(process.cwd(), "node_modules", "tsx", "dist", "cli.mjs");

  const res = spawnSync(process.execPath, [tsxNodeEntrypoint, entry, command], {
    env: process.env,
    encoding: "utf8",
    windowsHide: true,
  });

  if (res.error) throw new Error(res.error.message);

  const stdout = String(res.stdout ?? "").trim();
  const stderr = String(res.stderr ?? "").trim();

  let json: unknown | null = null;
  if (stdout) {
    try {
      json = JSON.parse(stdout);
    } catch {
      json = null;
    }
  }

  return { exitCode: res.status ?? 0, stdout, stderr, json };
}

function noStoreHeaders(contentType: string) {
  return {
    "Content-Type": contentType,
    "Cache-Control": "no-store",
  };
}

function sendJson(res: http.ServerResponse, status: number, value: unknown) {
  const body = JSON.stringify(value, null, 2);
  res.writeHead(status, noStoreHeaders("application/json; charset=utf-8"));
  res.end(body);
}

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c) => chunks.push(Buffer.isBuffer(c) ? c : Buffer.from(c)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

type HeartbeatConfig = {
  enabled: boolean;
  intervalMinutes: number;
};

type ConfigChangeAppliedReceipt = {
  kind: "CONFIG_CHANGE_APPLIED";
  ts: string;
  change: {
    key: "heartbeat";
    before: HeartbeatConfig | null;
    after: HeartbeatConfig;
    actor: { type: "api"; id: string };
    reason?: string;
  };
  integrity: {
    sha256: string;
  };
};

const HEARTBEAT_STATE_PATH =
  process.env.SINTRA_HEARTBEAT_STATE_PATH ||
  path.join(process.cwd(), "state", "heartbeat.json");

const RECEIPTS_DIR =
  process.env.SINTRA_RECEIPTS_DIR ||
  path.join(process.cwd(), "runs", "receipts");

// the JSONL file that /api/receipts tails (the UI uses this path directly)
const RECEIPTS_JSONL =
  process.env.SINTRA_RECEIPTS_JSONL ||
  path.join(process.cwd(), "runs", "receipts.jsonl");

function stableStringify(obj: unknown): string {
  const seen = new WeakSet<object>();
  const sorter = (value: any): any => {
    if (value && typeof value === "object") {
      if (seen.has(value)) return "[Circular]";
      seen.add(value);
      if (Array.isArray(value)) return value.map(sorter);
      const keys = Object.keys(value).sort();
      const out: Record<string, any> = {};
      for (const k of keys) out[k] = sorter(value[k]);
      return out;
    }
    return value;
  };
  return JSON.stringify(sorter(obj));
}

function validateHeartbeatPayload(body: any): HeartbeatConfig {
  if (!body || typeof body !== "object") throw new Error("INVALID_BODY");
  const enabled = body.enabled;
  const intervalMinutes = body.intervalMinutes;
  if (typeof enabled !== "boolean") throw new Error("INVALID_ENABLED");
  const interval =
    typeof intervalMinutes === "number" && Number.isFinite(intervalMinutes)
      ? Math.floor(intervalMinutes)
      : 10;
  if (interval < 1 || interval > 1440) throw new Error("INVALID_INTERVAL");
  if (enabled && (typeof intervalMinutes !== "number" || !Number.isFinite(intervalMinutes))) {
    throw new Error("MISSING_INTERVAL");
  }
  return { enabled, intervalMinutes: interval };
}

async function ensureDir(p: string) {
  await fsPromises.mkdir(p, { recursive: true });
}

async function atomicWriteJson(filePath: string, obj: unknown) {
  await ensureDir(path.dirname(filePath));
  const tmp = `${filePath}.tmp.${Date.now()}`;
  const raw = stableStringify(obj) + "\n";
  await fsPromises.writeFile(tmp, raw, "utf8");
  await fsPromises.rename(tmp, filePath);
}

async function readHeartbeatState(): Promise<HeartbeatConfig | null> {
  try {
    const raw = await fsPromises.readFile(HEARTBEAT_STATE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed.enabled === "boolean" &&
      typeof parsed.intervalMinutes === "number"
    ) {
      return { enabled: parsed.enabled, intervalMinutes: parsed.intervalMinutes };
    }
    return null;
  } catch {
    return null;
  }
}

async function writeConfigChangeAppliedReceipt(
  before: HeartbeatConfig | null,
  after: HeartbeatConfig,
  reason?: string
) {
  await ensureDir(RECEIPTS_DIR);
  const receiptBase: Omit<ConfigChangeAppliedReceipt, "integrity"> = {
    kind: "CONFIG_CHANGE_APPLIED",
    ts: new Date().toISOString(),
    change: {
      key: "heartbeat",
      before,
      after,
      actor: { type: "api", id: "operator-ui" },
      ...(reason ? { reason } : {}),
    },
  };
  const canonical = stableStringify(receiptBase);
  const sha256 = crypto.createHash("sha256").update(canonical).digest("hex");
  const receipt: ConfigChangeAppliedReceipt = {
    ...receiptBase,
    integrity: { sha256 },
  };
  const fileName = `${receipt.ts.replace(/[:.]/g, "-")}_CONFIG_CHANGE_APPLIED_${sha256.slice(0, 12)}.json`;
  const outPath = path.join(RECEIPTS_DIR, fileName);
  await fsPromises.writeFile(outPath, stableStringify(receipt) + "\n", "utf8");

  // also append to the canonical receipts.jsonl for the UI tail query
  try {
    await ensureDir(path.dirname(RECEIPTS_JSONL));
    await fsPromises.appendFile(RECEIPTS_JSONL, stableStringify(receipt) + "\n", "utf8");
  } catch {
    // if appending fails, don't block the API
    console.warn("failed to append heartbeat receipt to jsonl");
  }

  return { sha256, path: outPath, receipt };
}

function isSafeRunsPath(p: string): boolean {
  const norm = p.replace(/\\/g, "/");
  return norm === "runs" || norm.startsWith("runs/");
}

function resolveUnderCwd(rel: string) {
  const base = process.cwd();
  const target = path.resolve(base, rel);
  const baseResolved = path.resolve(base);
  if (!target.startsWith(baseResolved + path.sep) && target !== baseResolved) {
    throw new Error("path escapes workspace");
  }
  return target;
}

function listFilesRecursive(dir: string, limit: number): string[] {
  const out: string[] = [];
  const stack: string[] = [dir];

  while (stack.length && out.length < limit) {
    const cur = stack.pop()!;
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const e of entries) {
      const fp = path.join(cur, e.name);
      if (e.isDirectory()) {
        stack.push(fp);
        continue;
      }
      if (e.isFile()) out.push(fp);
      if (out.length >= limit) break;
    }
  }

  return out;
}

function tailJsonl(filePath: string, limit: number): unknown[] {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, "utf8");
  const lines = content.split(/\r?\n/).filter(Boolean);
  const slice = lines.slice(Math.max(0, lines.length - limit));
  const out: unknown[] = [];
  for (const line of slice) {
    try {
      out.push(JSON.parse(line));
    } catch {
      // ignore malformed
    }
  }
  return out;
}

function contentTypeFor(filePath: string) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  return "application/octet-stream";
}

function readStaticFile(staticDir: string, urlPath: string) {
  const clean = urlPath.split("?")[0]!.split("#")[0]!;
  const requested = clean === "/" ? "/index.html" : clean;
  const rel = requested.replace(/^\//, "");
  const filePath = path.resolve(staticDir, rel);
  const base = path.resolve(staticDir);
  if (!filePath.startsWith(base + path.sep) && filePath !== base) {
    return null;
  }
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return null;
  return {
    filePath,
    bytes: fs.readFileSync(filePath),
    contentType: contentTypeFor(filePath),
  };
}

export type OperatorUiServerHandle = {
  port: number;
  close: () => Promise<void>;
};

export async function startOperatorUiServer(opts?: { port?: number }): Promise<OperatorUiServerHandle> {
  const port = typeof opts?.port === "number" ? opts.port : Number(process.env.OPERATOR_UI_PORT || 3000);

  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const staticDir = path.join(__dirname, "static");

  const server = http.createServer(async (req, res) => {
    try {
      const method = String(req.method || "GET").toUpperCase();
      const u = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);

      if (method === "GET" && u.pathname === "/api/approvals") {
        const dir = path.join(process.cwd(), "runs", "approvals");
        const rows: any[] = [];
        if (fs.existsSync(dir)) {
          const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
          for (const f of files) {
            const fp = path.join(dir, f);
            try {
              const json = JSON.parse(fs.readFileSync(fp, "utf8"));
              rows.push({ file: path.join("runs", "approvals", f).replace(/\\/g, "/"), ...json });
            } catch {
              // ignore unreadable
            }
          }
        }
        sendJson(res, 200, { kind: "ApprovalsList", count: rows.length, approvals: rows });
        return;
      }

      if (method === "GET" && u.pathname === "/api/receipts") {
        const limit = Math.min(500, Math.max(0, Number(u.searchParams.get("limit") || 100)));
        const filePath = path.join(process.cwd(), "runs", "receipts.jsonl");
        const receipts = tailJsonl(filePath, limit);
        sendJson(res, 200, { kind: "ReceiptsTail", count: receipts.length, receipts });
        return;
      }

      if (method === "GET" && u.pathname === "/api/artifacts") {
        const prefix = (u.searchParams.get("prefix") || "runs").trim();
        if (!isSafeRunsPath(prefix)) {
          sendJson(res, 400, { kind: "BadRequest", reason: "prefix must be under runs/" });
          return;
        }
        const limit = Math.min(2000, Math.max(1, Number(u.searchParams.get("limit") || 500)));
        const abs = resolveUnderCwd(prefix);
        const files = fs.existsSync(abs) ? listFilesRecursive(abs, limit) : [];
        const rows = files.map((fp) => {
          const st = fs.statSync(fp);
          const rel = path.relative(process.cwd(), fp).replace(/\\/g, "/");
          return { path: rel, size: st.size, mtime_ms: st.mtimeMs };
        });
        sendJson(res, 200, { kind: "ArtifactsList", prefix, count: rows.length, files: rows });
        return;
      }

      if (method === "GET" && u.pathname === "/api/artifact") {
        const p = (u.searchParams.get("path") || "").trim();
        if (!p || !isSafeRunsPath(p)) {
          sendJson(res, 400, { kind: "BadRequest", reason: "path must be under runs/" });
          return;
        }
        const abs = resolveUnderCwd(p);
        if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
          sendJson(res, 404, { kind: "NotFound" });
          return;
        }
        const txt = fs.readFileSync(abs, "utf8");
        const contentType = contentTypeFor(abs);
        let json: unknown | null = null;
        if (path.extname(abs).toLowerCase() === ".json") {
          try {
            json = JSON.parse(txt);
          } catch {
            json = null;
          }
        }
        sendJson(res, 200, {
          kind: "ArtifactContent",
          path: p.replace(/\\/g, "/"),
          contentType,
          content: txt,
          json,
        });
        return;
      }

      if (method === "GET" && u.pathname === "/api/scheduler/history") {
        const jobId = (u.searchParams.get("job_id") || "").trim();
        const dir = path.join(process.cwd(), "runs", "scheduler-history");
        const rows: any[] = [];
        if (fs.existsSync(dir)) {
          const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
          for (const f of files) {
            if (jobId && !f.startsWith(jobId + ".")) continue;
            try {
              rows.push(JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
            } catch {
              // ignore
            }
          }
        }
        rows.sort((a, b) => new Date(b?.started_at || 0).getTime() - new Date(a?.started_at || 0).getTime());
        sendJson(res, 200, { kind: "SchedulerHistory", job_id: jobId || null, count: rows.length, rows });
        return;
      }

      if (method === "GET" && u.pathname === "/api/heartbeat") {
        const cfg = await readHeartbeatState();
        sendJson(res, 200, { kind: "HeartbeatState", config: cfg });
        return;
      }

      if (method === "POST" && u.pathname === "/api/heartbeat") {
        try {
          const raw = await readBody(req);
          let body: any;
          try {
            body = JSON.parse(raw || "{}");
          } catch {
            sendJson(res, 400, { kind: "HeartbeatUpdateError", ok: false, error: "INVALID_JSON" });
            return;
          }
          const next = validateHeartbeatPayload(body);
          const prev = await readHeartbeatState();
          await atomicWriteJson(HEARTBEAT_STATE_PATH, {
            ...next,
            updatedAt: new Date().toISOString(),
          });
          const { sha256, path: receiptPath } = await writeConfigChangeAppliedReceipt(
            prev,
            next,
            typeof body?.reason === "string" ? body.reason : undefined
          );
          sendJson(res, 200, {
            kind: "HeartbeatUpdated",
            ok: true,
            config: next,
            receipt: { kind: "CONFIG_CHANGE_APPLIED", sha256, path: receiptPath },
          });
        } catch (e: any) {
          const msg = String(e?.message || e);
          const code = msg === "INVALID_JSON" ? 400 : msg === "BODY_TOO_LARGE" ? 413 : 400;
          sendJson(res, code, {
            kind: "HeartbeatUpdateError",
            ok: false,
            error: msg,
          });
        }
        return;
      }

      if (method === "POST" && u.pathname === "/api/command") {
        const raw = await readBody(req);
        let body: any;
        try {
          body = JSON.parse(raw || "{}");
        } catch {
          sendJson(res, 400, { kind: "BadRequest", reason: "invalid JSON" });
          return;
        }

        const message = String(body?.message || "").trim();
        if (!message.startsWith("/")) {
          sendJson(res, 400, { kind: "BadRequest", reason: "message must start with /" });
          return;
        }
        if (message.length > 2000 || message.includes("\n")) {
          sendJson(res, 400, { kind: "BadRequest", reason: "message too large or contains newlines" });
          return;
        }

        const out = runEngineCliForUi(message);
        sendJson(res, 200, { kind: "OperatorUiCommandResult", ...out });
        return;
      }

      // static
      if (method === "GET") {
        const st = readStaticFile(staticDir, u.pathname);
        if (!st) {
          res.writeHead(404, noStoreHeaders("text/plain; charset=utf-8"));
          res.end("Not found");
          return;
        }
        res.writeHead(200, noStoreHeaders(st.contentType));
        res.end(st.bytes);
        return;
      }

      sendJson(res, 405, { kind: "MethodNotAllowed" });
    } catch (e: any) {
      sendJson(res, 500, { kind: "ServerError", reason: String(e?.message || e) });
    }
  });

  await new Promise<void>((resolve) => server.listen(port, "127.0.0.1", resolve));

  const actual = server.address();
  const actualPort = typeof actual === "object" && actual ? actual.port : port;

  return {
    port: actualPort,
    close: () => new Promise<void>((resolve, reject) => {
      server.close((err) => (err ? reject(err) : resolve()));
    }),
  };
}
