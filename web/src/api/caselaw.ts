import api from './client';
import type { CaseLaw } from '../types/legal';

export interface CaseLawSearchParams {
  query: string;
  jurisdiction?: string;
  court?: string;
  dateFrom?: string;
  dateTo?: string;
  practiceAreas?: string[];
  page?: number;
  limit?: number;
  sortBy?: 'relevance' | 'date' | 'citations';
}

export interface CaseLawSearchResult {
  cases: CaseLaw[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

export interface CitationNetwork {
  caseId: string;
  nodes: Array<{ id: string; label: string; year: number; citations: number }>;
  edges: Array<{ source: string; target: string; type: 'cites' | 'cited_by' }>;
}

export interface SavedSearch {
  id: string;
  name: string;
  params: CaseLawSearchParams;
  alertEnabled: boolean;
  lastRun?: string;
  newResults?: number;
  createdAt: string;
}

export const caselawAPI = {
  search: (params: CaseLawSearchParams) =>
    api.get<CaseLawSearchResult>('/caselaw/search', params as Record<string, unknown>),

  getCase: (id: string) =>
    api.get<CaseLaw>(`/caselaw/${id}`),

  getCitationNetwork: (id: string, depth?: number) =>
    api.get<CitationNetwork>(`/caselaw/${id}/citations`, depth ? { depth } : undefined),

  bookmark: (id: string) =>
    api.post<void>(`/caselaw/${id}/bookmark`),

  removeBookmark: (id: string) =>
    api.delete<void>(`/caselaw/${id}/bookmark`),

  getBookmarks: () =>
    api.get<CaseLaw[]>('/caselaw/bookmarks'),

  getSavedSearches: () =>
    api.get<SavedSearch[]>('/caselaw/saved-searches'),

  saveSearch: (data: { name: string; params: CaseLawSearchParams; alertEnabled?: boolean }) =>
    api.post<SavedSearch>('/caselaw/saved-searches', data),

  deleteSavedSearch: (id: string) =>
    api.delete<void>(`/caselaw/saved-searches/${id}`),

  getSuggestions: (query: string) =>
    api.get<string[]>('/caselaw/suggestions', { query }),
};
