import crypto from "node:crypto";
import { nowIso } from "../utils/clock.js";
import { loadSpeechSinks } from "./sinks/index.js";
import type { SpeechPayload } from "./sinks/types.js";
import { writeSpeechArtifact } from "./writeSpeechArtifact.js";
import { mapConfidenceToSpeech } from "./gradient/confidenceGradient.js";
import { redactSpeechText } from "./redaction/redactSpeech.js";
import { decideSpeech } from "./decideSpeech.js";

const SPEECH_DEBUG = process.env.SPEECH_DEBUG === "1";

function speechDebug(reason: string, details?: Record<string, unknown>): void {
  if (!SPEECH_DEBUG) return;
  try {
    const payload = {
      kind: "SpeechDebug",
      reason,
      ...(details ? { details } : {}),
    };
    process.stderr.write(`${JSON.stringify(payload)}\n`);
  } catch {
    // fail-open
  }
}

function envEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  const v = env.SPEECH_ENABLED;
  if (v == null || v === "") return true;
  return v === "1" || v.toLowerCase() === "true" || v.toLowerCase() === "yes";
}

function allowedCategory(category: string, env: NodeJS.ProcessEnv = process.env): boolean {
  const raw = String(env.SPEECH_CATEGORIES ?? "").trim();
  if (!raw) return true;
  const allow = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!allow.length) return true;
  return allow.includes(category);
}

function stableHash(input: string): string {
  return crypto.createHash("sha256").update(input).digest("hex");
}

function parseCsv(input: string | undefined | null): string[] {
  const raw = String(input ?? "").trim();
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const budgetByFingerprint = new Map<string, { base: number; used: number }>();
const silenceUntilByFingerprint = new Map<string, number>();
const lastSpokenAtByFingerprint = new Map<string, number>();

function parseVoiceBudgetFromEnv(env: NodeJS.ProcessEnv = process.env): number | null {
  const raw = String(env.SPEECH_VOICE_BUDGET ?? "").trim();
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

function normalizeConfidence(raw: number): number {
  if (!Number.isFinite(raw)) return 1;
  if (raw > 1) return Math.max(0, Math.min(1, raw / 100));
  return Math.max(0, Math.min(1, raw));
}

function severityForGate(meta?: SpeechPayload["meta"]): "low" | "medium" | "high" {
  const s = meta?.severity;
  if (s === "urgent") return "high";
  if (s === "warning") return "medium";
  return "low";
}

function redactionLevelForGate(decision: { redactionLevel: "low" | "medium" | "high" }):
  | "normal"
  | "strict"
  | "paranoid" {
  if (decision.redactionLevel === "high") return "paranoid";
  if (decision.redactionLevel === "medium") return "strict";
  return "normal";
}

function writeDecisionArtifact(input: {
  fingerprint: string;
  threadId: string | null;
  execution_id: string | null;
  category: string;
  timestamp: string;
  text_preview: string;
  decision: any;
  meta: SpeechPayload["meta"] | null;
}): void {
  if (process.env.SPEECH_ARTIFACTS !== "1") return;
  const suffix = stableHash(
    `${input.timestamp}|${input.category}|${input.threadId ?? ""}|${String(input.decision?.reason ?? "")}|${input.text_preview}`
  ).slice(0, 16);
  try {
    writeSpeechArtifact({
      dir: "speech-decisions",
      fingerprint: input.fingerprint,
      timestamp: input.timestamp,
      suffix,
      payload: {
        kind: "SpeechDecision",
        fingerprint: input.fingerprint,
        execution_id: input.execution_id,
        threadId: input.threadId,
        category: input.category,
        timestamp: input.timestamp,
        text_preview: input.text_preview,
        decision: input.decision,
        meta: input.meta,
      },
    });
  } catch {
    // fail-open
  }
}

export function speak(input: {
  text: string;
  category: string;
  fingerprint?: string;
  execution_id?: string;
  threadId?: string;
  timestamp?: string;
  meta?: SpeechPayload["meta"];
}): void {
  try {
    if (!envEnabled()) return;
    if (!allowedCategory(input.category)) return;

    const timestamp = input.timestamp ?? nowIso();
    const threadId = input.threadId ?? process.env.THREAD_ID ?? input.execution_id;

     const gateFingerprint = input.fingerprint ?? threadId ?? "speech";
     const nowMs = Date.now();

     // Hard silence window (sticky): if we've previously silenced, do not speak until expiration.
     const silenceUntil = silenceUntilByFingerprint.get(gateFingerprint);
     if (typeof silenceUntil === "number" && nowMs < silenceUntil) {
       speechDebug("SILENCE_WINDOW_ACTIVE", {
         fingerprint: gateFingerprint,
         category: input.category,
         now: nowMs,
         until: silenceUntil,
       });
       writeDecisionArtifact({
         fingerprint: gateFingerprint,
         threadId: threadId ?? null,
         execution_id: input.execution_id ?? null,
         category: input.category,
         timestamp,
         text_preview: String(input.text).slice(0, 180),
         decision: { allow: false, reason: "LOW_CONFIDENCE", silenceUntil },
         meta: input.meta ?? null,
       });
       return;
     }

     // Budget state (per fingerprint, per process).
     const baseBudget = parseVoiceBudgetFromEnv();
     const state = (() => {
       const existing = budgetByFingerprint.get(gateFingerprint);
       if (existing) {
         if (typeof baseBudget === "number") existing.base = baseBudget;
         return existing;
       }
       const initial = { base: typeof baseBudget === "number" ? baseBudget : Number.POSITIVE_INFINITY, used: 0 };
       budgetByFingerprint.set(gateFingerprint, initial);
       return initial;
     })();

     const budgetRemaining = Number.isFinite(state.base) ? Math.max(0, state.base - state.used) : 1_000_000_000;

     const confidence = typeof input.meta?.confidence === "number" ? normalizeConfidence(input.meta.confidence) : 1;
     const lastSpokenAt = lastSpokenAtByFingerprint.get(gateFingerprint);

     const decision = decideSpeech({
       confidence,
       severity: severityForGate(input.meta),
       budgetRemaining,
       lastSpokenAt,
       now: nowMs,
     });

     if (!decision.allow) {
       if (decision.reason === "LOW_CONFIDENCE") {
         speechDebug("LOW_CONFIDENCE", {
           fingerprint: gateFingerprint,
           category: input.category,
           confidence,
           min: 0.4,
           now: nowMs,
           silenceUntil: decision.silenceUntil ?? null,
         });
       }
       if (decision.reason === "BUDGET_EXHAUSTED") {
         speechDebug("BUDGET_EXHAUSTED", {
           fingerprint: gateFingerprint,
           category: input.category,
           remaining: budgetRemaining,
         });
       }
       if (decision.reason === "LOW_CONFIDENCE" && typeof decision.silenceUntil === "number") {
         silenceUntilByFingerprint.set(gateFingerprint, decision.silenceUntil);
       }

       writeDecisionArtifact({
         fingerprint: gateFingerprint,
         threadId: threadId ?? null,
         execution_id: input.execution_id ?? null,
         category: input.category,
         timestamp,
         text_preview: String(input.text).slice(0, 180),
         decision: {
           ...decision,
           budgetRemaining,
           lastSpokenAt: typeof lastSpokenAt === "number" ? lastSpokenAt : null,
         },
         meta: input.meta ?? null,
       });
       return;
     }

    // Apply redaction based on decision, but still allow explicit allow-categories to bypass.
    let text = input.text;
    let meta: SpeechPayload["meta"] | undefined = input.meta;
    const allowCats = parseCsv(process.env.SPEECH_REDACTION_ALLOW_CATEGORIES);
    const mappedLevel = redactionLevelForGate(decision);
    try {
      const redacted = redactSpeechText(text, allowCats, input.category, { level: mappedLevel });
      text = redacted.text;
      const hits = redacted.hits;
      if (hits.length || mappedLevel !== "normal") {
        meta = {
          ...(meta ?? {}),
          ...(hits.length ? { redaction_hits: hits } : {}),
          redaction_level: mappedLevel,
        };
      }
    } catch {
      // fail-open
    }

    // Budget decrement (exactly one per allowed speak).
    state.used += 1;
    lastSpokenAtByFingerprint.set(gateFingerprint, nowMs);
    if (Number.isFinite(state.base)) {
      meta = {
        ...(meta ?? {}),
        effective_voice_budget: state.base,
      };
    }

    writeDecisionArtifact({
      fingerprint: gateFingerprint,
      threadId: threadId ?? null,
      execution_id: input.execution_id ?? null,
      category: input.category,
      timestamp,
      text_preview: String(input.text).slice(0, 180),
      decision: {
        ...decision,
        budgetRemainingBefore: budgetRemaining,
        budgetRemainingAfter: Math.max(0, budgetRemaining - 1),
      },
      meta: meta ?? null,
    });

    const payload: SpeechPayload = {
      text,
      category: input.category,
      threadId: threadId || undefined,
      timestamp,
      meta,
    };

    const sinks = (() => {
      try {
        return loadSpeechSinks();
      } catch {
        return loadSpeechSinks({ ...process.env, SPEECH_SINKS: "console" });
      }
    })();

    if (process.env.SPEECH_ARTIFACTS === "1") {
      const suffix = stableHash(
        `${payload.timestamp}|${payload.category}|${payload.threadId ?? ""}|${payload.text}`
      ).slice(0, 16);

      try {
        writeSpeechArtifact({
          dir: "speech-lines",
          fingerprint: gateFingerprint,
          timestamp: payload.timestamp,
          suffix,
          payload: {
            kind: "SpeechLine",
            fingerprint: gateFingerprint,
            execution_id: input.execution_id ?? null,
            threadId: payload.threadId ?? null,
            category: payload.category,
            timestamp: payload.timestamp,
            text: payload.text,
            sinks: sinks.map((s) => s.name),
            meta: payload.meta ?? null,
          },
        });
      } catch {
        // fail-open
      }
    }

    for (const sink of sinks) {
      try {
        void Promise.resolve(sink.speak(payload)).catch(() => {
          // fail-open
        });
      } catch {
        // fail-open
      }
    }
  } catch {
    // fail-open
  }
}

export function speakText(
  text: string,
  category = "info",
  threadId?: string,
  opts?: { confidence?: number; fingerprint?: string; execution_id?: string; timestamp?: string }
): void {
  try {
    const useGradient = process.env.SPEECH_CONFIDENCE_GRADIENT === "1";
    const prefixEnabled = process.env.SPEECH_GRADIENT_PREFIX === "1";

    let meta: SpeechPayload["meta"] | undefined;
    let finalText = text;

    if (useGradient && typeof opts?.confidence === "number") {
      const g = mapConfidenceToSpeech(opts.confidence);
      meta = { confidence: g.confidence, severity: g.severity, cadence: g.cadence };
      if (prefixEnabled) finalText = `${g.prefix} ${finalText}`;
    }

    speak({
      text: finalText,
      category,
      threadId,
      fingerprint: opts?.fingerprint,
      execution_id: opts?.execution_id,
      timestamp: opts?.timestamp,
      meta,
    });
  } catch {
    // fail-open
  }
}
