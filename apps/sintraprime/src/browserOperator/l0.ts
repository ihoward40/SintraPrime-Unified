import fs from "node:fs";
import path from "node:path";
import { chromium, firefox, webkit, type BrowserType } from "playwright";

import { assertUrlSafeForL0 } from "../browser/l0/ssrfGuards.js";
import type { ArtifactRef } from "../artifacts/writeBrowserEvidence.js";
import { writeArtifactRelative } from "../artifacts/writeBrowserEvidence.js";
import { evidenceRollupSha256 } from "../receipts/evidenceRollup.js";

export type BrowserL0ArtifactRef = ArtifactRef;

function envBool(name: string, def: boolean): boolean {
  const v = process.env[name];
  if (v == null) return def;
  return ["1", "true", "yes", "on"].includes(String(v).toLowerCase());
}

function parseHostPatterns(raw?: string): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

export function getBrowserL0Config() {
  const allowData = envBool("BROWSER_L0_ALLOW_DATA", true);
  const allowHttp = envBool("BROWSER_L0_ALLOW_HTTP", false);
  const allowedHosts = parseHostPatterns(process.env.BROWSER_L0_ALLOWED_HOSTS);

  const allowedSchemes = new Set<string>(["https:"]);
  if (allowHttp) allowedSchemes.add("http:");
  if (allowData) allowedSchemes.add("data:");

  return { allowData, allowHttp, allowedSchemes, allowedHosts };
}

export function assertUrlAllowedByBrowserL0(rawUrl: string) {
  const cfg = getBrowserL0Config();
  assertUrlSafeForL0(rawUrl, {
    allowedSchemes: Array.from(cfg.allowedSchemes),
    allowedHosts: cfg.allowedHosts,
    requireAllowedHosts: true,
  });
}

function pickBrowser(name: string): BrowserType {
  const n = String(name || "chromium").trim().toLowerCase();
  if (n === "firefox") return firefox;
  if (n === "webkit") return webkit;
  return chromium;
}

function safeFilePart(value: string) {
  return String(value)
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 140);
}

function toPosix(p: string) {
  return p.replace(/\\/g, "/");
}

function runsDir() {
  return path.join(process.cwd(), "runs", "browser-l0");
}

function stepRunsDir(execution_id: string, step_id: string) {
  return path.join(runsDir(), safeFilePart(execution_id), safeFilePart(step_id));
}

function writeJson(filePath: string, value: unknown) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n", "utf8");
}

async function withBrowserPage<T>(args: {
  url: string;
  timeoutMs: number;
  fn: (page: import("playwright").Page, resp: import("playwright").Response | null) => Promise<T>;
}): Promise<T> {
  assertUrlAllowedByBrowserL0(args.url);

  const browserType = pickBrowser(String(process.env.PLAYWRIGHT_BROWSER ?? "chromium"));
  const headless = String(process.env.PLAYWRIGHT_HEADLESS ?? "true").trim().toLowerCase() !== "false";
  const slowMoRaw = process.env.PLAYWRIGHT_SLOW_MO;
  const slowMo = slowMoRaw ? Number(slowMoRaw) : 0;

  const browser = await browserType.launch({ headless, slowMo: Number.isFinite(slowMo) ? slowMo : 0 });
  const context = await browser.newContext({
    acceptDownloads: false,
    viewport: { width: 1280, height: 720 },
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });

  try {
    const page = await context.newPage();
    const resp = await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    return await args.fn(page, resp);
  } finally {
    await context.close().catch(() => void 0);
    await browser.close().catch(() => void 0);
  }
}

export async function browserL0Navigate(input: {
  execution_id: string;
  step_id: string;
  url: string;
  timeoutMs: number;
}) {
  assertUrlAllowedByBrowserL0(input.url);
  const out = await withBrowserPage({
    url: input.url,
    timeoutMs: input.timeoutMs,
    fn: async (page, resp) => {
      const title = await page.title().catch(() => null);
      return {
        final_url: page.url(),
        status: resp ? resp.status() : null,
        title,
        content_type: resp ? resp.headers()["content-type"] ?? null : null,
      };
    },
  });

  return {
    ok: true,
    status: 200,
    response: out,
    responseJson: out,
  };
}

export async function browserL0Screenshot(input: {
  execution_id: string;
  step_id: string;
  url: string;
  timeoutMs: number;
  fullPage?: boolean;
}) {
  assertUrlAllowedByBrowserL0(input.url);
  fs.mkdirSync(stepRunsDir(input.execution_id, input.step_id), { recursive: true });

  const relPng = toPosix(
    path.join(
      "runs",
      "browser-l0",
      safeFilePart(input.execution_id),
      safeFilePart(input.step_id),
      "screenshot.png"
    )
  );
  const relMeta = toPosix(
    path.join(
      "runs",
      "browser-l0",
      safeFilePart(input.execution_id),
      safeFilePart(input.step_id),
      "screenshot.meta.json"
    )
  );

  const maxBytesRaw = process.env.BROWSER_L0_MAX_SCREENSHOT_BYTES;
  const maxBytes = maxBytesRaw && Number.isFinite(Number(maxBytesRaw)) ? Math.max(1, Number(maxBytesRaw)) : 8_000_000;

  let final_url: string | null = null;
  let pngRef: ArtifactRef | null = null;

  await withBrowserPage({
    url: input.url,
    timeoutMs: input.timeoutMs,
    fn: async (page) => {
      final_url = page.url();
      const buf = await page.screenshot({ fullPage: input.fullPage ?? true, type: "png" });
      if (buf.length > maxBytes) {
        throw new Error(`browser.l0 screenshot too large (${buf.length} bytes > ${maxBytes})`);
      }
      pngRef = writeArtifactRelative(relPng, Buffer.from(buf), "image/png");
    },
  });

  if (!pngRef) {
    throw new Error("browser.l0 screenshot missing evidence ref");
  }
  const evidence: ArtifactRef[] = [pngRef];

  const evidence_rollup_sha256 = evidenceRollupSha256(evidence);
  const meta = {
    execution_id: input.execution_id,
    step_id: input.step_id,
    url: input.url,
    final_url,
    evidence,
    evidence_rollup_sha256,
    captured_at: new Date().toISOString(),
  };

  const metaRef = writeArtifactRelative(
    relMeta,
    Buffer.from(JSON.stringify(meta, null, 2) + "\n", "utf8"),
    "application/json"
  );
  evidence.push(metaRef);

  const response = {
    url: input.url,
    final_url,
    evidence,
    evidence_rollup_sha256: evidenceRollupSha256(evidence),
  };

  return { ok: true, status: 200, response, responseJson: response };
}

export async function browserL0DomExtract(input: {
  execution_id: string;
  step_id: string;
  url: string;
  timeoutMs: number;
  maxChars?: number;
}) {
  assertUrlAllowedByBrowserL0(input.url);
  fs.mkdirSync(stepRunsDir(input.execution_id, input.step_id), { recursive: true });

  const relHtml = toPosix(
    path.join("runs", "browser-l0", safeFilePart(input.execution_id), safeFilePart(input.step_id), "dom.html")
  );
  const relTxt = toPosix(
    path.join("runs", "browser-l0", safeFilePart(input.execution_id), safeFilePart(input.step_id), "dom.txt")
  );
  const relExtract = toPosix(
    path.join("runs", "browser-l0", safeFilePart(input.execution_id), safeFilePart(input.step_id), "extract.json")
  );

  const maxChars = typeof input.maxChars === "number" && Number.isFinite(input.maxChars) && input.maxChars > 0 ? input.maxChars : 250_000;

  const extracted = await withBrowserPage({
    url: input.url,
    timeoutMs: input.timeoutMs,
    fn: async (page, resp) => {
      const title = await page.title().catch(() => null);
      const html = await page.content().catch(() => "");
      const text = await page
        .evaluate(() => {
          const d = globalThis as any;
          const body = d?.document?.body;
          return body && typeof body.innerText === "string" ? body.innerText : "";
        })
        .catch(() => "");
      return {
        final_url: page.url(),
        status: resp ? resp.status() : null,
        content_type: resp ? resp.headers()["content-type"] ?? null : null,
        title,
        html,
        text,
      };
    },
  });

  const htmlOut = String(extracted.html ?? "").slice(0, maxChars);
  const textOut = String(extracted.text ?? "").slice(0, maxChars);

  const htmlRef = writeArtifactRelative(relHtml, Buffer.from(htmlOut, "utf8"), "text/html; charset=utf-8");
  const txtRef = writeArtifactRelative(relTxt, Buffer.from(textOut, "utf8"), "text/plain; charset=utf-8");

  const extractPayload = {
    execution_id: input.execution_id,
    step_id: input.step_id,
    url: input.url,
    final_url: extracted.final_url,
    http_status: extracted.status,
    content_type: extracted.content_type,
    title: extracted.title ?? null,
    truncated: {
      max_chars: maxChars,
      html_chars: htmlOut.length,
      text_chars: textOut.length,
    },
  };
  const extractRef = writeArtifactRelative(
    relExtract,
    Buffer.from(JSON.stringify(extractPayload, null, 2) + "\n", "utf8"),
    "application/json"
  );

  const evidence: ArtifactRef[] = [htmlRef, txtRef, extractRef];

  const response = {
    url: input.url,
    final_url: extracted.final_url,
    title: extracted.title ?? null,
    evidence,
    evidence_rollup_sha256: evidenceRollupSha256(evidence),
  };

  return { ok: true, status: 200, response, responseJson: response };
}
