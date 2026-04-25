import { z } from "zod";
import crypto from "node:crypto";

import type { WebSearchResponse, WebSearchResult } from "./types.js";

const ProviderName = "duckduckgo_instant_answer" as const;

const DefaultWarnings = [
  "DuckDuckGo Instant Answer API is not full web search; results may be sparse",
];

const CacheTtlMs = 5 * 60_000;
const CacheMaxEntries = 200;
const cache = new Map<string, { ts: number; value: WebSearchResponse }>();

function stableJsonStringify(value: unknown): string {
  const stable = (v: any): any => {
    if (v === null || v === undefined) return v;
    if (Array.isArray(v)) return v.map(stable);
    if (typeof v !== "object") return v;
    const keys = Object.keys(v).sort();
    const out: any = {};
    for (const k of keys) out[k] = stable(v[k]);
    return out;
  };
  return JSON.stringify(stable(value));
}

function sha256Hex(value: string): string {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function cacheKeyForQuery(query: string): string {
  return `${ProviderName}|${query.trim().toLowerCase()}`;
}

function pruneCache(now: number) {
  // Drop expired first
  for (const [k, v] of cache.entries()) {
    if (now - v.ts > CacheTtlMs) cache.delete(k);
  }
  // Enforce size bound (oldest-first)
  if (cache.size <= CacheMaxEntries) return;
  const entries = Array.from(cache.entries()).sort((a, b) => a[1].ts - b[1].ts);
  for (const [k] of entries) {
    cache.delete(k);
    if (cache.size <= CacheMaxEntries) break;
  }
}

const RelatedTopicSchema: z.ZodType<any> = z.lazy(() =>
  z.union([
    z.object({
      Name: z.string().optional(),
      Topics: z.array(RelatedTopicSchema).optional(),
    }).passthrough(),
    z.object({
      Text: z.string().optional(),
      FirstURL: z.string().optional(),
      Result: z.string().optional(),
      Icon: z.any().optional(),
    }).passthrough(),
  ])
);

const DuckDuckGoInstantAnswerSchema = z.object({
  Heading: z.string().optional(),
  AbstractText: z.string().optional(),
  AbstractURL: z.string().optional(),
  AbstractSource: z.string().optional(),
  RelatedTopics: z.array(RelatedTopicSchema).optional(),
});

function uniqByUrl(results: WebSearchResult[], max: number): WebSearchResult[] {
  const seen = new Set<string>();
  const out: WebSearchResult[] = [];
  for (const r of results) {
    const url = String(r.url || "").trim();
    if (!url) continue;
    if (seen.has(url)) continue;
    seen.add(url);
    out.push(r);
    if (out.length >= max) break;
  }
  return out;
}

function flattenRelatedTopics(input: unknown): Array<{ Text?: string; FirstURL?: string }> {
  const out: Array<{ Text?: string; FirstURL?: string }> = [];

  const visit = (node: any) => {
    if (!node || typeof node !== "object") return;
    if (typeof node.Text === "string" || typeof node.FirstURL === "string") {
      out.push({ Text: node.Text, FirstURL: node.FirstURL });
      return;
    }
    if (Array.isArray(node.Topics)) {
      for (const t of node.Topics) visit(t);
    }
  };

  if (Array.isArray(input)) {
    for (const n of input) visit(n);
  }
  return out;
}

export function parseDuckDuckGoInstantAnswerResults(args: {
  query: string;
  json: unknown;
  maxResults: number;
}): WebSearchResponse {
  const rawSha256 = sha256Hex(stableJsonStringify(args.json));
  const parsed = DuckDuckGoInstantAnswerSchema.safeParse(args.json);
  if (!parsed.success) {
    return {
      provider: ProviderName,
      query: args.query,
      results: [],
      partial: true,
      warnings: [...DefaultWarnings, "DuckDuckGo response did not match expected shape"],
      rawSha256,
    };
  }

  const data = parsed.data;
  const results: WebSearchResult[] = [];

  const abstractUrl = typeof data.AbstractURL === "string" ? data.AbstractURL.trim() : "";
  const abstractText = typeof data.AbstractText === "string" ? data.AbstractText.trim() : "";
  const heading = typeof data.Heading === "string" ? data.Heading.trim() : "";

  if (abstractUrl) {
    results.push({
      title: heading || data.AbstractSource || args.query,
      url: abstractUrl,
      snippet: abstractText || null,
      provider: ProviderName,
    });
  }

  const related = flattenRelatedTopics(data.RelatedTopics);
  for (const r of related) {
    const url = typeof r.FirstURL === "string" ? r.FirstURL.trim() : "";
    const text = typeof r.Text === "string" ? r.Text.trim() : "";
    if (!url || !text) continue;
    results.push({
      title: text,
      url,
      snippet: null,
      provider: ProviderName,
    });
  }

  const limited = uniqByUrl(results, Math.max(0, args.maxResults));
  const partial = limited.length === 0;

  return {
    provider: ProviderName,
    query: args.query,
    results: limited,
    partial,
    warnings: partial
      ? [...DefaultWarnings, "No results returned from DuckDuckGo Instant Answer API"]
      : [...DefaultWarnings],
    rawSha256,
  };
}

export async function webSearchDuckDuckGoInstantAnswer(input: {
  query: string;
  maxResults?: number;
  timeoutMs?: number;
}): Promise<WebSearchResponse> {
  const query = String(input.query || "").trim();
  if (!query) {
    return {
      provider: ProviderName,
      query,
      results: [],
      partial: true,
      warnings: [...DefaultWarnings, "Missing query"],
    };
  }
  if (query.length > 512) {
    return {
      provider: ProviderName,
      query,
      results: [],
      partial: true,
      warnings: [...DefaultWarnings, "Query too long"],
    };
  }

  const maxResults = Math.min(20, Math.max(1, input.maxResults ?? 8));
  const timeoutMs = Math.min(20_000, Math.max(500, input.timeoutMs ?? 8_000));

  const now = Date.now();
  pruneCache(now);
  const key = cacheKeyForQuery(query);
  const cached = cache.get(key);
  if (cached && now - cached.ts <= CacheTtlMs) {
    return {
      ...cached.value,
      cache: { hit: true, ttlMs: CacheTtlMs },
    };
  }

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const url =
      "https://api.duckduckgo.com/?" +
      new URLSearchParams({
        q: query,
        format: "json",
        no_html: "1",
        skip_disambig: "1",
        t: "sintraprime",
      }).toString();

    const resp = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      headers: {
        accept: "application/json",
      },
    });

    if (!resp.ok) {
      return {
        provider: ProviderName,
        query,
        results: [],
        partial: true,
        warnings: [...DefaultWarnings, `DuckDuckGo HTTP ${resp.status}`],
      };
    }

    const json = (await resp.json().catch(() => null)) as unknown;
    const parsed = parseDuckDuckGoInstantAnswerResults({ query, json, maxResults });
    const value: WebSearchResponse = { ...parsed, cache: { hit: false, ttlMs: CacheTtlMs } };
    cache.set(key, { ts: now, value });
    pruneCache(Date.now());
    return value;
  } catch (e: any) {
    const msg = e?.name === "AbortError" ? "DuckDuckGo request timed out" : `DuckDuckGo request failed: ${String(e?.message || e)}`;
    return {
      provider: ProviderName,
      query,
      results: [],
      partial: true,
      warnings: [...DefaultWarnings, msg],
    };
  } finally {
    clearTimeout(t);
  }
}
