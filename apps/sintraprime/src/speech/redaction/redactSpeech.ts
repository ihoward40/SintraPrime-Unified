import type { RedactionLevel } from "./confidenceEscalation.js";

export function redactSpeechText(
  text: string,
  allowCategories: string[],
  category: string,
  opts?: { level?: RedactionLevel }
): { text: string; hits: string[] } {
  try {
    if (allowCategories.includes(category)) {
      return { text, hits: [] };
    }

    const level: RedactionLevel = opts?.level ?? "normal";

    let out = text;
    const hits: string[] = [];

    const rules: Array<{ re: RegExp; tag: string }> = [
      { re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, tag: "email" },
      { re: /\b\d{3}-\d{2}-\d{4}\b/g, tag: "ssn" },
    ];

    if (level === "strict" || level === "paranoid") {
      rules.push(
        { re: /\bhttps?:\/\/\S+/gi, tag: "url" },
        { re: /\b[a-f0-9]{16,}\b/gi, tag: "token" }
      );
    }

    if (level === "paranoid") {
      rules.push(
        { re: /\b\d{4,}\b/g, tag: "long_number" },
        { re: /\b[A-Z0-9_-]{8,}\b/gi, tag: "identifier" }
      );
    }

    for (const { re, tag } of rules) {
      out = out.replace(re, () => {
        hits.push(tag);
        return "[REDACTED]";
      });
    }

    return { text: out, hits };
  } catch {
    return { text, hits: [] };
  }
}
