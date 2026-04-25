import type { SpeechPayload, SpeechSink } from "./types.js";

export const consoleSink: SpeechSink = {
  name: "console",
  speak(payload: SpeechPayload) {
    // Preserve prior behavior: the speech tiers already include their own prefix.
    process.stderr.write(`${payload.text}\n`);
  },
};
