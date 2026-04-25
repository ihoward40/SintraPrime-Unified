export type WebSearchResult = {
  title: string;
  url: string;
  snippet: string | null;
  provider: string;
};

export type WebSearchResponse = {
  provider: string;
  query: string;
  results: WebSearchResult[];
  partial: boolean;
  warnings: string[];
  rawSha256?: string;
  cache?: {
    hit: boolean;
    ttlMs: number;
  };
};
