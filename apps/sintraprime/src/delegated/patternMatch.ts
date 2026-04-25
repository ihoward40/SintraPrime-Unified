import { normalizeCommand } from "../dsl/normalizeCommand.js";

function escapeRegex(s: string) {
  return s.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&");
}

export function normalizePattern(pattern: string): string {
  return normalizeCommand(String(pattern ?? ""));
}

export function patternToRegex(pattern: string): RegExp {
  const normalized = normalizePattern(pattern);
  // Very small, boring matcher: '*' matches any run of non-newline characters.
  // No '?' or character classes.
  const parts = normalized.split("*").map(escapeRegex);
  const source = "^" + parts.join("[\\s\\S]*") + "$";
  return new RegExp(source, "i");
}

export function patternMatchesCommand(pattern: string, command: string): boolean {
  const rx = patternToRegex(pattern);
  return rx.test(normalizeCommand(command));
}
