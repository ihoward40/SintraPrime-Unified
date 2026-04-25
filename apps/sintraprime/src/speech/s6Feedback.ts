import { shouldEmitSpeechToStderr } from "./speechTiers.js";
import { writeSpeechArtifact } from "./writeSpeechArtifact.js";
import { getRequalificationStatus, type RequalificationStatus } from "./getRequalificationStatus.js";
import { renderRequalificationSpeech } from "./renderRequalificationSpeech.js";
import { renderConfidenceSpeech } from "./renderConfidenceSpeech.js";
import { speak } from "./speak.js";

export function emitSpeechS6(input: {
  fingerprint: string;
  execution_id: string;
  now_iso: string;
  requalification?: { prev: RequalificationStatus; curr: RequalificationStatus };
  confidence?: { prev: any; curr: any };
}): { wrote?: { file: string } } {
  const rqPrevRaw = input.requalification?.prev ?? {};
  const rqCurrRaw = input.requalification?.curr ?? {};
  const rqPrev = getRequalificationStatus(rqPrevRaw);
  const rqCurr = getRequalificationStatus(rqCurrRaw);

  const rqLine = input.requalification ? renderRequalificationSpeech(rqPrev, rqCurr) : "";
  const confLine = input.confidence ? renderConfidenceSpeech(input.confidence.prev, input.confidence.curr) : "";

  if (!rqLine && !confLine) return {};

  const payload = {
    kind: "SpeechS6Feedback",
    fingerprint: input.fingerprint,
    execution_id: input.execution_id,
    now_iso: input.now_iso,
    requalification: input.requalification
      ? {
          prev: rqPrev,
          curr: rqCurr,
          line: rqLine || null,
        }
      : null,
    confidence: input.confidence
      ? {
          prev: input.confidence.prev ?? null,
          curr: input.confidence.curr ?? null,
          line: confLine || null,
        }
      : null,
  };

  const wrote = writeSpeechArtifact({
    dir: "speech-feedback",
    fingerprint: input.fingerprint,
    timestamp: input.now_iso,
    payload,
  });

  if (shouldEmitSpeechToStderr()) {
    if (rqLine) {
      speak({
        text: `[S6] ${rqLine}`,
        category: "autonomy",
        fingerprint: input.fingerprint,
        execution_id: input.execution_id,
        threadId: process.env.THREAD_ID,
        timestamp: input.now_iso,
      });
    }
    if (confLine) {
      speak({
        text: `[S6] ${confLine}`,
        category: "confidence",
        fingerprint: input.fingerprint,
        execution_id: input.execution_id,
        threadId: process.env.THREAD_ID,
        timestamp: input.now_iso,
      });
    }
  }

  return { wrote };
}
