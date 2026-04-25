import { readConfidence } from "../confidence/updateConfidence.js";
import { isRequalificationEnabled, readRequalificationState } from "../requalification/requalification.js";
import { shouldEmitSpeechToStderr } from "./speechTiers.js";
import { writeSpeechArtifact } from "./writeSpeechArtifact.js";
import { speak } from "./speak.js";

function normalizeRetryAfter(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const s = value.trim();
  return s ? s : null;
}

export function emitSpeechS5(input: {
  fingerprint: string;
  execution_id: string;
  now_iso: string;
  current: any;
  autonomy_mode: string;
  autonomy_mode_effective: string;
}): { wrote?: { file: string } } {
  const confidence = (() => {
    try {
      return readConfidence(input.fingerprint).confidence;
    } catch {
      return null;
    }
  })();

  const requalification_state = (() => {
    try {
      if (!isRequalificationEnabled()) return null;
      const s = readRequalificationState(input.fingerprint);
      return s?.state ?? null;
    } catch {
      return null;
    }
  })();

  const payload = {
    kind: "SpeechS5Status",
    fingerprint: input.fingerprint,
    execution_id: input.execution_id,
    now_iso: input.now_iso,
    status: input.current?.status ?? null,
    autonomy_mode: input.autonomy_mode,
    autonomy_mode_effective: input.autonomy_mode_effective,
    throttle_reason: input.current?.throttle_reason ?? null,
    retry_after: normalizeRetryAfter(input.current?.retry_after),
    confidence,
    requalification_state,
  };

  const wrote = writeSpeechArtifact({
    dir: "speech-status",
    fingerprint: input.fingerprint,
    timestamp: input.now_iso,
    payload,
  });

  if (shouldEmitSpeechToStderr()) {
    const parts: string[] = [];
    parts.push(`status=${String(payload.status)}`);
    parts.push(`mode=${payload.autonomy_mode_effective}`);
    if (payload.throttle_reason) parts.push(`throttle=${payload.throttle_reason}`);
    if (payload.requalification_state) parts.push(`requal=${payload.requalification_state}`);
    if (typeof payload.confidence === "number") parts.push(`confidence=${payload.confidence}`);
    speak({
      text: `[S5] ${parts.join(" ")}`,
      category: "autonomy",
      fingerprint: input.fingerprint,
      execution_id: input.execution_id,
      threadId: process.env.THREAD_ID,
      timestamp: input.now_iso,
    });
  }

  return { wrote };
}
