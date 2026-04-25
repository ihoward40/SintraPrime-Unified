import express from "express";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { sendMessage } from "../sendMessage.js";
import { getLastNLines } from "./streaming.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = Number(process.env.UI_PORT || 3000);
const RUNS_DIR = path.resolve(process.cwd(), "runs");
const EXPORTS_DIR = path.resolve(process.cwd(), "exports");
const CLIENT_DIST = path.join(__dirname, "client", "dist");
const LEGACY_PUBLIC = path.join(__dirname, "public");

app.use(express.json({ limit: "100kb" }));

// Simple in-memory cache with TTL
const cache = new Map();

async function withCacheAsync(key, ttlMs, fn) {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < ttlMs) {
    return cached.data;
  }
  const data = await fn();
  cache.set(key, { data, timestamp: Date.now() });
  return data;
}

function safeReadJson(absPath) {
  try {
    return JSON.parse(fs.readFileSync(absPath, "utf8"));
  } catch {
    return null;
  }
}

async function safeReadJsonAsync(absPath) {
  try {
    const content = await fsp.readFile(absPath, "utf8");
    return JSON.parse(content);
  } catch {
    return null;
  }
}

function parseIsoOrNull(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const t = Date.parse(value);
  return Number.isFinite(t) ? t : null;
}

function bestTimestampIso(obj) {
  const candidates = [
    obj?.finished_at,
    obj?.started_at,
    obj?.created_at,
    obj?.captured_at,
    obj?.approved_at,
    obj?.written_at,
    obj?.guard_evaluated_at,
    obj?.requested_at,
    obj?.generated_at,
  ];
  for (const c of candidates) {
    const t = parseIsoOrNull(c);
    if (t !== null) return new Date(t).toISOString();
  }
  return null;
}

function resolveUnderRuns(relPath) {
  const abs = path.resolve(RUNS_DIR, String(relPath || ""));
  const base = RUNS_DIR.endsWith(path.sep) ? RUNS_DIR : RUNS_DIR + path.sep;
  if (!abs.startsWith(base) && abs !== RUNS_DIR) {
    throw new Error("path escapes runs/");
  }
  return abs;
}

function resolveUnderExports(maybeAbsOrRelPath) {
  const raw = String(maybeAbsOrRelPath || "");
  const abs = path.isAbsolute(raw) ? path.resolve(raw) : path.resolve(process.cwd(), raw);
  const base = EXPORTS_DIR.endsWith(path.sep) ? EXPORTS_DIR : EXPORTS_DIR + path.sep;
  if (!abs.startsWith(base) && abs !== EXPORTS_DIR) {
    throw new Error("path escapes exports/");
  }
  return abs;
}

function sanitizeFilePart(value) {
  const s = String(value ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 160);
}

function findLatestAuditZipForExecution(executionId) {
  const safeId = sanitizeFilePart(executionId);
  const dir = path.join(EXPORTS_DIR, "audit_exec");
  if (!fs.existsSync(dir)) return null;

  const prefix = `audit_${safeId}.zip`;
  const candidates = fs
    .readdirSync(dir)
    .filter((name) => name === prefix || (name.startsWith(prefix + "_") && /^_\d+$/.test(name.slice((prefix + "_").length))))
    .map((name) => {
      const abs = path.join(dir, name);
      try {
        const st = fs.statSync(abs);
        return st.isFile() ? { name, abs, mtimeMs: st.mtimeMs } : null;
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  if (!candidates.length) return null;
  candidates.sort((a, b) => {
    if (a.mtimeMs !== b.mtimeMs) return b.mtimeMs - a.mtimeMs;
    return String(b.name).localeCompare(String(a.name));
  });
  return candidates[0].abs;
}

// ---- READ-ONLY APIs ----

app.get("/api/approvals", async (_req, res) => {
  const items = await withCacheAsync("approvals", 5000, async () => {
    const dir = path.join(RUNS_DIR, "approvals");
    try {
      await fsp.access(dir);
    } catch {
      return [];
    }
    const files = await fsp.readdir(dir);
    const jsonFiles = files.filter((f) => f.endsWith(".json"));
    const results = await Promise.all(
      jsonFiles.map((f) => safeReadJsonAsync(path.join(dir, f)))
    );
    return results.filter(Boolean);
  });
  res.json(items);
});

app.get("/api/receipts", async (req, res) => {
  const limit = Math.min(500, Math.max(0, Number(req.query.limit || 100)));
  const cacheKey = `receipts:${limit}`;
  const out = await withCacheAsync(cacheKey, 5000, async () => {
    const file = path.join(RUNS_DIR, "receipts.jsonl");
    try {
      await fsp.access(file);
      // Use memory-efficient streaming for large JSONL files
      return await getLastNLines(file, limit);
    } catch {
      return [];
    }
  });
  res.json(out);
});

app.get("/api/artifacts", async (req, res) => {
  const prefix = String(req.query.prefix || "");
  let base;
  try {
    base = resolveUnderRuns(prefix);
  } catch {
    return res.status(400).json({ error: "prefix must be under runs/" });
  }

  try {
    await fsp.access(base);
  } catch {
    return res.json([]);
  }

  const walk = async (d) => {
    const entries = await fsp.readdir(d, { withFileTypes: true });
    const results = await Promise.all(
      entries.map(async (e) => {
        if (e.isDirectory()) {
          return walk(path.join(d, e.name));
        } else {
          return [{ path: path.relative(RUNS_DIR, path.join(d, e.name)).replace(/\\\\/g, "/") }];
        }
      })
    );
    return results.flat();
  };

  const artifacts = await walk(base);
  res.json(artifacts);
});

app.get("/api/file", (req, res) => {
  const rel = req.query.path;
  if (!rel) return res.status(400).json({ error: "path required" });

  let abs;
  try {
    abs = resolveUnderRuns(String(rel));
  } catch {
    return res.status(403).end();
  }

  if (!fs.existsSync(abs)) return res.status(404).end();

  // v1: JSON-only for safety.
  res.json(safeReadJson(abs));
});

app.get("/api/raw", (req, res) => {
  const rel = req.query.path;
  if (!rel) return res.status(400).json({ error: "path required" });

  let abs;
  try {
    abs = resolveUnderRuns(String(rel));
  } catch {
    return res.status(403).end();
  }

  if (!fs.existsSync(abs)) return res.status(404).end();

  res.setHeader("Content-Type", "application/octet-stream");
  res.setHeader("Content-Disposition", `attachment; filename="${path.basename(abs)}"`);
  fs.createReadStream(abs).pipe(res);
});

app.get("/api/export", (req, res) => {
  const rel = req.query.path;
  if (!rel) return res.status(400).json({ error: "path required" });

  let abs;
  try {
    abs = resolveUnderExports(String(rel));
  } catch {
    return res.status(403).end();
  }

  if (!fs.existsSync(abs)) return res.status(404).end();

  res.setHeader("Content-Type", "application/octet-stream");
  res.setHeader("Content-Disposition", `attachment; filename="${path.basename(abs)}"`);
  fs.createReadStream(abs).pipe(res);
});

app.get("/api/execution/:executionId", (req, res) => {
  const executionId = String(req.params.executionId || "").trim();
  if (!executionId) return res.status(400).json({ error: "executionId required" });

  // Receipt: scan receipts.jsonl for the last matching line.
  let receipt = null;
  try {
    const p = path.join(RUNS_DIR, "receipts.jsonl");
    if (fs.existsSync(p)) {
      const lines = fs.readFileSync(p, "utf8").split(/\r?\n/).filter(Boolean);
      for (let i = lines.length - 1; i >= 0; i -= 1) {
        try {
          const row = JSON.parse(lines[i]);
          if (row?.execution_id === executionId) {
            receipt = row;
            break;
          }
        } catch {
          // ignore
        }
      }
    }
  } catch {
    // ignore
  }

  const approvalAbs = path.join(RUNS_DIR, "approvals", `${executionId}.json`);
  const approval = fs.existsSync(approvalAbs) ? safeReadJson(approvalAbs) : null;

  const prestateDir = path.join(RUNS_DIR, "prestate");
  const prestate_paths = fs.existsSync(prestateDir)
    ? fs
        .readdirSync(prestateDir)
        .filter((f) => f.startsWith(`${executionId}.`) && f.endsWith(".json"))
        .map((f) => `prestate/${f}`)
        .sort((a, b) => a.localeCompare(b))
    : [];

  // Artifacts: walk one level under runs/ and include files with the execution prefix.
  const artifact_items = [];
  if (fs.existsSync(RUNS_DIR)) {
    for (const ent of fs.readdirSync(RUNS_DIR, { withFileTypes: true })) {
      if (!ent.isDirectory()) continue;
      const dir = ent.name;
      if (dir === "approvals" || dir === "prestate" || dir === "scheduler-history") continue;
      const dirAbs = path.join(RUNS_DIR, dir);
      for (const f of fs.readdirSync(dirAbs)) {
        if (!f || (!f.startsWith(`${executionId}.`) && f !== `${executionId}.json`)) continue;
        const rel = `${dir}/${f}`;
        const json = safeReadJson(path.join(dirAbs, f));
        artifact_items.push({
          path: rel,
          timestamp: json ? bestTimestampIso(json) : null,
          kind: json?.kind || json?.event || null,
        });
      }
    }
  }
  artifact_items.sort((a, b) => String(a.path).localeCompare(String(b.path)));

  const zipAbs = findLatestAuditZipForExecution(executionId);
  const bundle = zipAbs
    ? {
        zip_path: zipAbs.replace(/\\/g, "/"),
        download_url: `/api/execution/${encodeURIComponent(executionId)}/bundle`,
      }
    : null;

  res.json({
    execution_id: executionId,
    receipt,
    approval,
    prestate_paths,
    artifact_items,
    rollback: null,
    bundle,
  });
});

app.get("/api/execution/:executionId/bundle", (req, res) => {
  const executionId = String(req.params.executionId || "").trim();
  if (!executionId) return res.status(400).json({ error: "executionId required" });

  const zipAbs = findLatestAuditZipForExecution(executionId);
  if (!zipAbs) return res.status(404).json({ error: "bundle not found" });

  let abs;
  try {
    abs = resolveUnderExports(zipAbs);
  } catch {
    return res.status(403).end();
  }

  res.setHeader("Content-Type", "application/octet-stream");
  res.setHeader("Content-Disposition", `attachment; filename="${path.basename(abs)}"`);
  fs.createReadStream(abs).pipe(res);
});

// ---- COMMAND FORWARDER (SAFE) ----

app.post("/api/command", async (req, res) => {
  const { message } = req.body || {};
  if (typeof message !== "string" || !message.startsWith("/")) {
    return res.status(400).json({ error: "command must start with /" });
  }

  const threadId = String(req.headers["x-thread-id"] || "ui_thread");

  const out = await sendMessage({
    type: "user_message",
    message,
    threadId,
  });

  res.json(out);
});

// ---- CACHE MANAGEMENT ----

app.delete("/api/cache", (_req, res) => {
  cache.clear();
  res.json({ message: "Cache cleared successfully" });
});

// ---- SCOPED LOCAL CLI: audit export (per execution) ----

app.post("/api/audit/export", (req, res) => {
  const execution_id = String(req.body?.execution_id || "").trim();
  if (!execution_id) return res.status(400).json({ error: "execution_id required" });
  if (!/^[a-zA-Z0-9_.:-]{1,220}$/.test(execution_id)) {
    return res.status(400).json({ error: "invalid execution_id" });
  }

  const cliEntry = path.join(process.cwd(), "src", "cli", "run-command.ts");
  const args = ["--loader", "tsx", cliEntry, `/audit export ${execution_id}`];

  const proc = spawnSync(process.execPath, args, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      // Ensure the UI-triggered export is deterministic and not sensitive to ambient strictness.
      STRICT_AGENT_OUTPUT: process.env.STRICT_AGENT_OUTPUT === "1" ? "1" : "0",
    },
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });

  const stdout = String(proc.stdout || "").trim();
  const stderr = String(proc.stderr || "").trim();

  if (proc.status !== 0) {
    return res.status(500).json({ error: "audit export failed", exit: proc.status, stderr: stderr.slice(0, 2000) });
  }

  try {
    const json = stdout ? JSON.parse(stdout) : null;
    return res.json({ ok: true, result: json, stderr: stderr || null });
  } catch {
    return res.json({ ok: true, result: null, raw_stdout: stdout.slice(0, 2000), stderr: stderr || null });
  }
});

// ---- Static UI ----

// Legacy: served under /legacy
if (fs.existsSync(LEGACY_PUBLIC)) {
  app.use("/legacy", express.static(LEGACY_PUBLIC));
}

// React build: served at /
if (fs.existsSync(CLIENT_DIST) && fs.existsSync(path.join(CLIENT_DIST, "index.html"))) {
  app.use(express.static(CLIENT_DIST));
  app.get("/", (_req, res) => res.sendFile(path.join(CLIENT_DIST, "index.html")));
  app.get("/*", (_req, res) => res.sendFile(path.join(CLIENT_DIST, "index.html")));
} else if (fs.existsSync(LEGACY_PUBLIC) && fs.existsSync(path.join(LEGACY_PUBLIC, "index.html"))) {
  // If React isn't built yet, serve legacy at /
  app.use(express.static(LEGACY_PUBLIC));
}

app.listen(PORT, "127.0.0.1", () => {
  console.log(`[UI] Operator console at http://localhost:${PORT}`);
  if (fs.existsSync(LEGACY_PUBLIC)) console.log(`[UI] Legacy UI at http://localhost:${PORT}/legacy`);
});
