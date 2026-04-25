import type { SpeechSink } from "./types.js";
import { spawn } from "node:child_process";

export const osTtsSink: SpeechSink = {
  name: "os-tts",
  speak({ text }) {
    try {
      if (process.platform === "darwin") {
        const child = spawn("say", [text], { stdio: "ignore", windowsHide: true });
        child.unref();
        return;
      }

      if (process.platform === "win32") {
        // Avoid injection/quoting issues by passing text via stdin.
        const child = spawn(
          "powershell",
          [
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Add-Type -AssemblyName System.Speech; $t=[Console]::In.ReadToEnd(); (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak($t)",
          ],
          { stdio: ["pipe", "ignore", "ignore"], windowsHide: true }
        );
        child.unref();
        try {
          child.stdin.end(text);
        } catch {
          // ignore
        }
      }
    } catch {
      // fail-open
    }
  },
};
