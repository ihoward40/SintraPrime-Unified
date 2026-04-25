import type { SpeechPayload, SpeechSink } from "./types.js";
import http from "node:http";
import https from "node:https";

const WEBHOOK_URL = process.env.SPEECH_WEBHOOK_URL;
const SECRET = process.env.SPEECH_WEBHOOK_SECRET;

function postJson(urlString: string, payload: any, headers: Record<string, string>) {
  const url = new URL(urlString);
  const body = Buffer.from(JSON.stringify(payload));

  const lib = url.protocol === "https:" ? https : http;

  const req = lib.request(
    {
      protocol: url.protocol,
      hostname: url.hostname,
      port: url.port ? Number(url.port) : undefined,
      path: `${url.pathname}${url.search}`,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": String(body.length),
        ...headers,
      },
    },
    (res) => {
      // Best-effort: drain to avoid socket leaks.
      res.resume();
    }
  );

  // Ensure this never keeps the process alive.
  try {
    req.setTimeout(1500, () => req.destroy());
    req.on("socket", (socket) => {
      try {
        socket.unref();
      } catch {
        // ignore
      }
    });
  } catch {
    // ignore
  }

  req.on("error", () => {
    // fail-open
  });

  req.end(body);
}

export const webhookSink: SpeechSink = {
  name: "webhook",
  speak(payload: SpeechPayload) {
    if (!WEBHOOK_URL) return;
    try {
      postJson(WEBHOOK_URL, payload, SECRET ? { "X-Speech-Secret": SECRET } : {});
    } catch {
      // fail-open
    }
  },
};
