import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { chromium, firefox, webkit, type BrowserType, type Page } from "playwright";
import crypto from "node:crypto";

import type { ControlConfig } from "../clean/config.js";
import { appendRunLedgerLine, ensureRunDirs, runRoot } from "./runArtifacts.js";

type Settings = {
  enabled: boolean;
  recordVideo: boolean;
  recordScreenshots: boolean;
  slowMoMs: number;
  headless: boolean;
  redactSecrets: boolean;
  browser: "chromium" | "firefox" | "webkit";
  systems: string[];
  urls: Record<string, string>;
};

function parseCsv(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function boolFromEnv(v: string | undefined): boolean | null {
  if (v === undefined) return null;
  const s = String(v).trim().toLowerCase();
  if (s === "1" || s === "true") return true;
  if (s === "0" || s === "false") return false;
  return null;
}

function intFromEnv(v: string | undefined): number | null {
  if (v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function pickBrowser(name: string): { name: Settings["browser"]; type: BrowserType } {
  const n = String(name || "chromium").trim().toLowerCase();
  if (n === "firefox") return { name: "firefox", type: firefox };
  if (n === "webkit") return { name: "webkit", type: webkit };
  return { name: "chromium", type: chromium };
}

function getSettings(env: NodeJS.ProcessEnv, config: ControlConfig | null): Settings {
  const cfg = config?.watch_mode ?? {};

  const enabled = boolFromEnv(env.WATCH_MODE) ?? Boolean(cfg.enabled);
  const recordVideo = boolFromEnv(env.WATCH_MODE_RECORD_VIDEO) ?? (cfg.record_video ?? true);
  const recordScreenshots = boolFromEnv(env.WATCH_MODE_RECORD_SCREENSHOTS) ?? (cfg.record_screenshots ?? true);
  const slowMoMs = intFromEnv(env.PLAYWRIGHT_SLOW_MO) ?? (cfg.slow_mo_ms ?? 0);
  const headless = boolFromEnv(env.PLAYWRIGHT_HEADLESS) ?? (cfg.headless ?? true);
  const redactSecrets = boolFromEnv(env.WATCH_MODE_REDACT_SECRETS) ?? (cfg.redact_secrets ?? true);
  const { name: browser } = pickBrowser(String(env.PLAYWRIGHT_BROWSER ?? "chromium"));

  const systems = parseCsv(env.WATCH_SYSTEMS || "notion,make,slack");
  const urls: Record<string, string> = {
    notion: String(env.WATCH_NOTION_URL ?? "").trim(),
    make: String(env.WATCH_MAKE_URL ?? "").trim(),
    slack: String(env.WATCH_SLACK_URL ?? "").trim(),
  };

  return { enabled, recordVideo, recordScreenshots, slowMoMs, headless, redactSecrets, browser, systems, urls };
}

async function autoScroll(page: Page) {
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(700);
  }
}

async function applyRedactionCss(page: Page) {
  const css = `
    input[type="password"],
    input[name*="token" i],
    input[name*="api" i],
    input[name*="key" i],
    textarea[name*="token" i],
    textarea[name*="api" i],
    textarea[name*="key" i] {
      filter: blur(8px) !important;
    }
  `;
  await page.addStyleTag({ content: css }).catch(() => void 0);
}

function safeFilePart(value: string) {
  return String(value)
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 140);
}

function utcStamp(d = new Date()) {
  const iso = d.toISOString();
  // 2026-01-12T14:32:18.123Z -> 20260112T143218Z
  return iso.replace(/[-:]/g, "").replace(/\..*Z$/, "Z");
}

function sha256FileHex(filePath: string) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function findNewestWebm(dir: string): string | null {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files = entries
      .filter((e) => e.isFile() && e.name.toLowerCase().endsWith(".webm"))
      .map((e) => ({ file: path.join(dir, e.name), stat: fs.statSync(path.join(dir, e.name)) }))
      .sort((a, b) => b.stat.mtimeMs - a.stat.mtimeMs);
    return files[0]?.file ?? null;
  } catch {
    return null;
  }
}

function tryConvertWebmToMp4(inputWebm: string, outMp4: string): boolean {
  const res = spawnSync(
    "ffmpeg",
    ["-y", "-i", inputWebm, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", outMp4],
    { stdio: "ignore" }
  );
  return res.status === 0;
}

export async function runWatchModeTour(params: {
  execution_id: string;
  config?: ControlConfig | null;
  env?: NodeJS.ProcessEnv;
  note?: string;
}) {
  const env = params.env ?? process.env;
  const settings = getSettings(env, params.config ?? null);
  if (!settings.enabled) return;

  const executionId = String(params.execution_id);
  const { screenDir, screenshotsDir, tourDir } = ensureRunDirs(executionId);

  const createdArtifacts: string[] = [];

  appendRunLedgerLine(executionId, {
    ts: new Date().toISOString(),
    kind: "watch_mode",
    stage: "start",
    note: params.note ?? null,
    systems: settings.systems,
    headless: settings.headless,
    slow_mo_ms: settings.slowMoMs,
  });

  const { type: browserType } = pickBrowser(settings.browser);

  for (const system of settings.systems) {
    const url = settings.urls[system];
    if (!url) {
      appendRunLedgerLine(executionId, {
        ts: new Date().toISOString(),
        kind: "watch_mode",
        stage: "skip",
        system,
        reason: "missing_url",
      });
      continue;
    }

    const userDataDir = path.join(screenDir, "_profile", system);
    const videoTmpDir = path.join(screenDir, "_video_tmp", system);
    fs.mkdirSync(videoTmpDir, { recursive: true });

    const context = await browserType.launchPersistentContext(userDataDir, {
      headless: settings.headless,
      slowMo: settings.slowMoMs,
      viewport: { width: 1280, height: 720 },
      recordVideo: settings.recordVideo ? { dir: videoTmpDir, size: { width: 1280, height: 720 } } : undefined,
    });

    try {
      const page = context.pages()[0] ?? (await context.newPage());
      if (settings.redactSecrets) await applyRedactionCss(page);

      appendRunLedgerLine(executionId, {
        ts: new Date().toISOString(),
        kind: "watch_mode",
        stage: "navigate",
        system,
        url,
      });

      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
      await page.waitForTimeout(1200);

      if (settings.recordScreenshots) {
        const stamp = utcStamp();
        const tourBefore = path.join(tourDir, `${system}__tour__before__${stamp}.png`);
        await page
          .screenshot({ path: tourBefore, fullPage: true })
          .catch(() => void 0);

        createdArtifacts.push(path.relative(runRoot(executionId), tourBefore).replace(/\\/g, "/"));

        // Back-compat: keep the older stable filename too.
        await page
          .screenshot({ path: path.join(screenshotsDir, `${system}.before.png`), fullPage: true })
          .catch(() => void 0);
      }

      await autoScroll(page).catch(() => void 0);

      await page.reload({ waitUntil: "domcontentloaded" }).catch(() => void 0);
      await page.waitForTimeout(1200);

      if (settings.recordScreenshots) {
        const stamp = utcStamp();
        const tourAfter = path.join(tourDir, `${system}__tour__after__${stamp}.png`);
        await page
          .screenshot({ path: tourAfter, fullPage: true })
          .catch(() => void 0);

        createdArtifacts.push(path.relative(runRoot(executionId), tourAfter).replace(/\\/g, "/"));

        // Back-compat: keep the older stable filename too.
        await page
          .screenshot({ path: path.join(screenshotsDir, `${system}.after.png`), fullPage: true })
          .catch(() => void 0);
      }
    } finally {
      await context.close().catch(() => void 0);
    }

    if (settings.recordVideo) {
      const newest = findNewestWebm(videoTmpDir);
      if (newest) {
        const webmOut = path.join(screenDir, `${system}.webm`);
        try {
          fs.copyFileSync(newest, webmOut);
        } catch {
          // ignore
        }

        createdArtifacts.push(path.relative(runRoot(executionId), webmOut).replace(/\\/g, "/"));

        const mp4Out = path.join(screenDir, `${system}.mp4`);
        const converted = tryConvertWebmToMp4(webmOut, mp4Out);

        if (converted) createdArtifacts.push(path.relative(runRoot(executionId), mp4Out).replace(/\\/g, "/"));

        appendRunLedgerLine(executionId, {
          ts: new Date().toISOString(),
          kind: "watch_mode",
          stage: "video",
          system,
          mp4_converted: converted,
          mp4: converted ? mp4Out.replace(/\\/g, "/") : null,
          webm: webmOut.replace(/\\/g, "/"),
        });
      }
    }
  }

  appendRunLedgerLine(executionId, {
    ts: new Date().toISOString(),
    kind: "watch_mode",
    stage: "finish",
  });

  return createdArtifacts;
}

export async function captureWatchStepScreenshots(params: {
  execution_id: string;
  phase_id: string;
  step_id: string;
  step_ordinal: number;
  config?: ControlConfig | null;
  env?: NodeJS.ProcessEnv;
}) {
  const env = params.env ?? process.env;
  const settings = getSettings(env, params.config ?? null);

  // Step screenshots are still gated by WATCH_MODE.
  if (!settings.enabled) return null;
  if (String(env.WATCH_STEP_SCREENSHOTS ?? "0").trim() !== "1") return null;

  const executionId = String(params.execution_id);
  const phaseId = safeFilePart(params.phase_id);
  const stepId = String(params.step_id);
  const stepOrdinal = Number.isFinite(params.step_ordinal) ? params.step_ordinal : 0;
  const capturedAt = new Date();
  const capturedAtIso = capturedAt.toISOString();
  const stamp = utcStamp(capturedAt);

  const { stepsDir } = ensureRunDirs(executionId);
  const root = runRoot(executionId);

  const { type: browserType } = pickBrowser(settings.browser);
  const out: Array<{ system: string; path: string; sha256: string; captured_at: string }> = [];

  for (const system of settings.systems) {
    const url = settings.urls[system];
    if (!url) continue;

    const userDataDir = path.join(path.join(root, "screen"), "_profile", system);
    const context = await browserType.launchPersistentContext(userDataDir, {
      headless: settings.headless,
      slowMo: settings.slowMoMs,
      viewport: { width: 1280, height: 720 },
    });

    const fileName = `${phaseId}__${String(stepOrdinal).padStart(2, "0")}__${safeFilePart(stepId)}__${system}__${stamp}.png`;
    const absPath = path.join(stepsDir, fileName);

    try {
      const page = context.pages()[0] ?? (await context.newPage());
      if (settings.redactSecrets) await applyRedactionCss(page);
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: absPath, fullPage: true });
      const rel = path.relative(root, absPath).replace(/\\/g, "/");
      const sha256 = sha256FileHex(absPath);
      out.push({ system, path: rel, sha256, captured_at: capturedAtIso });
    } catch {
      // best-effort
    } finally {
      await context.close().catch(() => void 0);
    }
  }

  appendRunLedgerLine(executionId, {
    ts: new Date().toISOString(),
    kind: "watch_mode",
    stage: "step_screenshot",
    step_id: stepId,
    phase_id: params.phase_id,
    step_ordinal: stepOrdinal,
    screenshots: out,
  });

  return out;
}
