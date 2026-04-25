import type { SpeechPayload, SpeechSink } from "./types.js";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { spawn } from "node:child_process";

const SPEECH_DEBUG = process.env.SPEECH_DEBUG === "1";

let last = Promise.resolve();

async function enqueue<T>(fn: () => Promise<T>): Promise<T> {
  const run = last.then(fn, fn);
  last = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

function debug(message: string): void {
  if (!SPEECH_DEBUG) return;
  try {
    process.stderr.write(`${message}\n`);
  } catch {
    // ignore
  }
}

function safeSlug(input: string): string {
  return String(input)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 40);
}

function getOutputDir(env: NodeJS.ProcessEnv = process.env): string {
  return String(env.ELEVEN_OUTPUT_DIR ?? "runs/speech-elevenlabs");
}

function selectVoiceId(payload: SpeechPayload, env: NodeJS.ProcessEnv = process.env): string | null {
  const category = String(payload.category ?? "").toLowerCase();

  // Category->voice indirection is optional and fully env-controlled.
  const categoryMap: Record<string, string> = {
    system: "ELEVEN_VOICE_ANDROID",
    warning: "ELEVEN_VOICE_ORACLE",
    error: "ELEVEN_VOICE_PROSECUTOR",
    critical: "ELEVEN_VOICE_DRAGON",
    success: "ELEVEN_VOICE_SAGE",
    info: "ELEVEN_VOICE_NARRATOR",
    debug: "ELEVEN_VOICE_WARRIOR",
    legal: "ELEVEN_VOICE_JUDGE",
  };

  const mappedKey = categoryMap[category];
  const mappedVoice = mappedKey ? env[mappedKey] : undefined;

  const explicitDefault = env.ELEVEN_VOICE_DEFAULT;
  const chosen = (mappedVoice && String(mappedVoice).trim()) || (explicitDefault && String(explicitDefault).trim());

  return chosen ? String(chosen) : null;
}

async function elevenTtsMp3(params: {
  apiKey: string;
  voiceId: string;
  text: string;
  modelId: string;
  stability: number;
  similarityBoost: number;
  useSpeakerBoost: boolean;
}): Promise<Buffer> {
  const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${params.voiceId}`, {
    method: "POST",
    headers: {
      Accept: "audio/mpeg",
      "Content-Type": "application/json",
      "xi-api-key": params.apiKey,
    },
    body: JSON.stringify({
      text: params.text,
      model_id: params.modelId,
      voice_settings: {
        stability: params.stability,
        similarity_boost: params.similarityBoost,
        use_speaker_boost: params.useSpeakerBoost,
      },
    }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => "");
    throw new Error(`ElevenLabs HTTP ${response.status}: ${errText.slice(0, 300)}`);
  }

  const audioBuffer = await response.arrayBuffer();
  return Buffer.from(audioBuffer);
}

function tryAutoPlay(filePath: string): void {
  const enabled = String(process.env.ELEVEN_AUTO_PLAY ?? "0") === "1";
  if (!enabled) return;

  try {
    if (process.platform === "win32") {
      const child = spawn(
        "powershell",
        ["-NoProfile", "-NonInteractive", "-Command", `Start-Process \"${filePath}\"`],
        { stdio: "ignore", windowsHide: true }
      );
      child.unref();
      return;
    }

    if (process.platform === "darwin") {
      const child = spawn("afplay", [filePath], { stdio: "ignore", windowsHide: true });
      child.unref();
      return;
    }

    // Linux: try to open with default handler.
    const child = spawn("xdg-open", [filePath], { stdio: "ignore", windowsHide: true });
    child.unref();
  } catch {
    // fail-open
  }
}

export const elevenLabsSink: SpeechSink = {
  name: "elevenlabs",

  speak(payload: SpeechPayload) {
    // Keep speech fail-open. Never throw from sinks.
    void enqueue(async () => {
      const apiKey = process.env.ELEVEN_API_KEY;
      if (!apiKey) {
        debug("[speech:elevenlabs] ELEVEN_API_KEY missing; skipping");
        return;
      }

      const voiceId = selectVoiceId(payload);
      if (!voiceId) {
        debug("[speech:elevenlabs] No voice id configured (set ELEVEN_VOICE_DEFAULT or category-specific vars); skipping");
        return;
      }

      const text = String(payload.text ?? "");
      if (!text.trim()) return;

      // Conservative defaults; can be overridden via env.
      const modelId = String(process.env.ELEVEN_MODEL_ID ?? "eleven_multilingual_v2");
      const stability = Number(process.env.ELEVEN_STABILITY ?? "0.5");
      const similarityBoost = Number(process.env.ELEVEN_SIMILARITY_BOOST ?? "0.5");
      const useSpeakerBoost = String(process.env.ELEVEN_USE_SPEAKER_BOOST ?? "1") === "1";

      const audio = await elevenTtsMp3({
        apiKey,
        voiceId,
        text,
        modelId,
        stability: Number.isFinite(stability) ? stability : 0.5,
        similarityBoost: Number.isFinite(similarityBoost) ? similarityBoost : 0.5,
        useSpeakerBoost,
      });

      const outputDir = getOutputDir();
      if (!existsSync(outputDir)) await mkdir(outputDir, { recursive: true });

      const timestamp = String(payload.timestamp ?? new Date().toISOString()).replace(/[:.]/g, "-");
      const category = safeSlug(payload.category ?? "speech");
      const filename = `speech_${timestamp}_${category}.mp3`;
      const filePath = join(outputDir, filename);

      await writeFile(filePath, audio);
      tryAutoPlay(filePath);
      debug(`[speech:elevenlabs] wrote ${filePath} (${audio.length} bytes)`);
    }).catch((err) => {
      debug(`[speech:elevenlabs] error: ${String((err as any)?.message ?? err)}`);
    });
  },
};
