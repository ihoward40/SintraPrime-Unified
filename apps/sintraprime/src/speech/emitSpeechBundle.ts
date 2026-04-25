import { getEnabledSpeechTiers } from "./speechTiers.js";
import { emitSpeechS3 } from "./s3Deltas.js";
import { emitSpeechS5 } from "./s5Status.js";
import { emitSpeechS6 } from "./s6Feedback.js";

export function emitSpeechBundle(input: {
  fingerprint: string;
  execution_id: string;
  now_iso: string;
  prior_by_fingerprint: any | null;
  current: any;
  autonomy_mode: string;
  autonomy_mode_effective: string;
  s6?: {
    requalification?: { prev: any; curr: any };
    confidence?: { prev: any; curr: any };
  };
  env?: NodeJS.ProcessEnv;
}): { s3?: { file: string }; s5?: { file: string } } {
  const tiers = getEnabledSpeechTiers(input.env);
  const out: { s3?: { file: string }; s5?: { file: string } } = {};

  if (tiers.has("S3")) {
    const r = emitSpeechS3({
      fingerprint: input.fingerprint,
      execution_id: input.execution_id,
      now_iso: input.now_iso,
      prior: input.prior_by_fingerprint,
      current: input.current,
    });
    if (r.wrote) out.s3 = r.wrote;
  }

  if (tiers.has("S5")) {
    const r = emitSpeechS5({
      fingerprint: input.fingerprint,
      execution_id: input.execution_id,
      now_iso: input.now_iso,
      current: input.current,
      autonomy_mode: input.autonomy_mode,
      autonomy_mode_effective: input.autonomy_mode_effective,
    });
    if (r.wrote) out.s5 = r.wrote;
  }

  if (tiers.has("S6") && (input.s6?.requalification || input.s6?.confidence)) {
    emitSpeechS6({
      fingerprint: input.fingerprint,
      execution_id: input.execution_id,
      now_iso: input.now_iso,
      requalification: input.s6?.requalification,
      confidence: input.s6?.confidence,
    });
  }

  return out;
}
