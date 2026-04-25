import type { SpeechSink } from "./types.js";
import { consoleSink } from "./consoleSink.js";
import { webhookSink } from "./webhookSink.js";
import { osTtsSink } from "./osTtsSink.js";
import { elevenLabsSink } from "./elevenLabsSink.js";

function parseList(value: string | undefined): string[] {
  return String(value ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function loadSpeechSinks(env: NodeJS.ProcessEnv = process.env): SpeechSink[] {
  const names = parseList(env.SPEECH_SINKS) || [];

  const all: Record<string, SpeechSink> = {
    console: consoleSink,
    webhook: webhookSink,
    "os-tts": osTtsSink,
    elevenlabs: elevenLabsSink,
  };

  const selected = (names.length ? names : ["console"])
    .map((n) => all[n])
    .filter((s): s is SpeechSink => Boolean(s));

  // Fail-safe: never return an empty sink list (avoid silent loss of stderr output).
  return selected.length ? selected : [consoleSink];
}
