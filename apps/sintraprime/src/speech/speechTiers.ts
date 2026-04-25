function parseList(input: string): Set<string> {
  const raw = String(input ?? "").trim();
  if (!raw) return new Set();
  return new Set(
    raw
      .split(/[,\s+|]+/g)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
  );
}

export type SpeechTier = "S3" | "S5" | "S6";

export function getEnabledSpeechTiers(env: NodeJS.ProcessEnv = process.env): Set<SpeechTier> {
  const tiers = parseList(env.SPEECH_TIERS || "");
  const single = String(env.SPEECH_TIER || "").trim();
  if (single) tiers.add(single.toUpperCase());

  const enabled: Set<SpeechTier> = new Set();
  for (const t of tiers) {
    if (t === "S3" || t === "S5") enabled.add(t);
    if (t === "S6") enabled.add("S6");
    if (t === "S3+S5" || t === "S5+S3") {
      enabled.add("S3");
      enabled.add("S5");
    }
    if (t === "S6+S5" || t === "S5+S6") {
      enabled.add("S5");
      enabled.add("S6");
    }
    if (t === "S3+S6" || t === "S6+S3") {
      enabled.add("S3");
      enabled.add("S6");
    }
    if (t === "S3+S5+S6" || t === "S6+S5+S3" || t === "S5+S3+S6") {
      enabled.add("S3");
      enabled.add("S5");
      enabled.add("S6");
    }
  }
  return enabled;
}

export function isSpeechEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  // Off by default; opt-in by selecting at least one tier.
  return getEnabledSpeechTiers(env).size > 0;
}

export function shouldEmitSpeechToStderr(env: NodeJS.ProcessEnv = process.env): boolean {
  // We keep this explicit in case future policy wants artifacts-only.
  return isSpeechEnabled(env);
}
