import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import puppeteer from "puppeteer";

import { ensureRunDirs, runRoot } from "../watch/runArtifacts.js";
import { BrowserOperatorPayloadSchema, type BrowserOperatorPayload } from "../schemas/BrowserOperator.schema.js";

function utcStamp(d = new Date()) {
  const iso = d.toISOString();
  return iso.replace(/[-:]/g, "").replace(/\..*Z$/, "Z");
}

function safeFilePart(value: string) {
  return String(value)
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 140);
}

function sha256FileHex(filePath: string) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

export type BrowserOperatorRunResult = {
  ok: boolean;
  status: number;
  response: unknown;
  responseJson: unknown;
  screenshots?: Array<{
    system: "browser_operator";
    path: string;
    sha256: string;
    captured_at: string;
  }>;
};

export async function runBrowserOperatorStep(params: {
  execution_id: string;
  step_id: string;
  url: string;
  payload: unknown;
}) : Promise<BrowserOperatorRunResult> {
  const parsed: BrowserOperatorPayload = BrowserOperatorPayloadSchema.parse(params.payload ?? {});

  const { stepsDir } = ensureRunDirs(params.execution_id);
  const stepDir = path.join(stepsDir, "browser_operator");
  fs.mkdirSync(stepDir, { recursive: true });

  const screenshots: BrowserOperatorRunResult["screenshots"] = [];

  const headless = parsed.options?.headless ?? true;
  const slowMo = parsed.options?.slow_mo_ms ?? 0;
  const viewport = parsed.options?.viewport ?? { width: 1280, height: 720 };
  const navigationTimeout = parsed.options?.navigation_timeout_ms ?? 60_000;
  const actionTimeout = parsed.options?.action_timeout_ms ?? 30_000;

  const browser = await puppeteer.launch({
    headless,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({
      width: viewport.width ?? 1280,
      height: viewport.height ?? 720,
    });

    const outputs: Record<string, unknown> = {};

    const takeScreenshot = async (name: string, fullPage: boolean) => {
      const stamp = utcStamp();
      const filename = `${safeFilePart(params.step_id)}__${safeFilePart(name)}__${stamp}.png`;
      const abs = path.join(stepDir, filename);
      await page.screenshot({ path: abs, fullPage });
      const rel = path.relative(runRoot(params.execution_id), abs).replace(/\\/g, "/");
      screenshots?.push({
        system: "browser_operator",
        path: rel,
        sha256: sha256FileHex(abs),
        captured_at: new Date().toISOString(),
      });
      return rel;
    };

    for (const action of parsed.actions) {
      if (action.type === "navigate") {
        const target = action.url ?? params.url;
        await page.goto(target, {
          waitUntil: action.wait_until ?? "domcontentloaded",
          timeout: action.timeout_ms ?? navigationTimeout,
        });
        continue;
      }

      if (action.type === "wait_for_selector") {
        await page.waitForSelector(action.selector, {
          timeout: action.timeout_ms ?? actionTimeout,
        });
        continue;
      }

      if (action.type === "wait_ms") {
        await new Promise((resolve) => setTimeout(resolve, action.ms));
        continue;
      }

      if (action.type === "click") {
        await page.waitForSelector(action.selector, { timeout: action.timeout_ms ?? actionTimeout });
        await page.click(action.selector);
        continue;
      }

      if (action.type === "type") {
        await page.waitForSelector(action.selector, { timeout: action.timeout_ms ?? actionTimeout });
        await page.type(action.selector, action.text);
        continue;
      }

      if (action.type === "extract_text") {
        await page.waitForSelector(action.selector, { timeout: action.timeout_ms ?? actionTimeout });
        const text = await page.$eval(action.selector, (el) => (el.textContent ?? "").trim());
        const key = action.key ?? `extract:${action.selector}`;
        outputs[key] = text;
        continue;
      }

      if (action.type === "screenshot") {
        const name = action.name ?? "screenshot";
        const rel = await takeScreenshot(name, action.full_page ?? true);
        outputs[`screenshot:${name}`] = rel;
        continue;
      }

      // Exhaustive guard (should be unreachable due to Zod parse)
      const _never: never = action;
      void _never;
    }

    const response = {
      kind: "BrowserOperatorResult",
      url: params.url,
      outputs,
      screenshots,
    };

    return {
      ok: true,
      status: 200,
      response,
      responseJson: response,
      screenshots,
    };
  } finally {
    await browser.close().catch(() => void 0);
  }
}
