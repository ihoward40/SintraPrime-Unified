import { writeSpeechArtifact } from "./writeSpeechArtifact.js";
import { shouldEmitSpeechToStderr } from "./speechTiers.js";
import { speak } from "./speak.js";

export type SpeechDelta = {
  field: string;
  from: unknown;
  to: unknown;
  severity: "info" | "warn" | "error";
};

function normalizeRetryAfter(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const s = value.trim();
  return s ? s : null;
}

function stableStringify(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function changed(a: unknown, b: unknown): boolean {
  return stableStringify(a) !== stableStringify(b);
}

export function computeS3Deltas(input: {
  prior: any;
  current: any;
}): SpeechDelta[] {
  const prior = input.prior ?? null;
  const current = input.current ?? null;
  if (!prior || !current) return [];

  const deltas: SpeechDelta[] = [];

  const priorStatus = prior?.status;
  const currentStatus = current?.status;
  if (changed(priorStatus, currentStatus)) {
    const severity: SpeechDelta["severity"] =
      currentStatus === "failed" || currentStatus === "denied" ? "error" : currentStatus === "throttled" ? "warn" : "info";
    deltas.push({ field: "status", from: priorStatus ?? null, to: currentStatus ?? null, severity });
  }

  const priorThrottle = prior?.throttle_reason ?? null;
  const currentThrottle = current?.throttle_reason ?? null;
  if (changed(priorThrottle, currentThrottle)) {
    deltas.push({ field: "throttle_reason", from: priorThrottle, to: currentThrottle, severity: "warn" });
  }

  const priorRetry = normalizeRetryAfter(prior?.retry_after);
  const currentRetry = normalizeRetryAfter(current?.retry_after);
  if (changed(priorRetry, currentRetry)) {
    deltas.push({ field: "retry_after", from: priorRetry, to: currentRetry, severity: "info" });
  }

  return deltas;
}

export function emitSpeechS3(input: {
  fingerprint: string;
  execution_id: string;
  now_iso: string;
  prior: any | null;
  current: any;
}): { wrote?: { file: string } } {
  const deltas = computeS3Deltas({ prior: input.prior, current: input.current });
  if (!deltas.length) return {};

  const payload = {
    kind: "SpeechS3Delta",
    fingerprint: input.fingerprint,
    execution_id: input.execution_id,
    now_iso: input.now_iso,
    deltas,
  };

  const wrote = writeSpeechArtifact({
    dir: "speech-deltas",
    fingerprint: input.fingerprint,
    timestamp: input.now_iso,
    payload,
  });

  if (shouldEmitSpeechToStderr()) {
    const headline = deltas
      .map((d) => `${d.field}: ${String(d.from ?? "∅")} → ${String(d.to ?? "∅")}`)
      .join("; ");
    speak({
      text: `[S3] ${headline}`,
      category: "deltas",
      fingerprint: input.fingerprint,
      execution_id: input.execution_id,
      threadId: process.env.THREAD_ID,
      timestamp: input.now_iso,
    });
  }

  return { wrote };
}
