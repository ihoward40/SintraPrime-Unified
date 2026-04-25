import api from './client';
import type { Case, Motion, CaseLaw, TrustDoctrine, UCCFiling, LegalAlert } from '../types/legal';

export const legalAPI = {
  // Cases
  getCases: (params?: { status?: string; practiceArea?: string; page?: number; limit?: number }) =>
    api.get<Case[]>('/legal/cases', params as Record<string, unknown>),

  getCase: (id: string) =>
    api.get<Case>(`/legal/cases/${id}`),

  createCase: (data: Partial<Case>) =>
    api.post<Case>('/legal/cases', data),

  updateCase: (id: string, data: Partial<Case>) =>
    api.patch<Case>(`/legal/cases/${id}`, data),

  deleteCase: (id: string) =>
    api.delete<void>(`/legal/cases/${id}`),

  // Motions
  getMotions: (caseId?: string) =>
    api.get<Motion[]>('/legal/motions', caseId ? { caseId } : undefined),

  draftMotion: (data: { caseId: string; type: string; context: string }) =>
    api.post<{ content: string; suggestedTitle: string }>('/legal/motions/draft', data),

  fileMotion: (id: string) =>
    api.post<Motion>(`/legal/motions/${id}/file`),

  // Case Law
  searchCaseLaw: (params: { query: string; jurisdiction?: string; dateFrom?: string; dateTo?: string; practiceAreas?: string[] }) =>
    api.get<CaseLaw[]>('/legal/caselaw/search', params as Record<string, unknown>),

  getCaseLaw: (id: string) =>
    api.get<CaseLaw>(`/legal/caselaw/${id}`),

  bookmarkCase: (id: string) =>
    api.post<void>(`/legal/caselaw/${id}/bookmark`),

  // Trust Law
  getTrustDoctrines: (params?: { category?: string; jurisdiction?: string }) =>
    api.get<TrustDoctrine[]>('/legal/trust/doctrines', params as Record<string, unknown>),

  generateTrustDocument: (data: { type: string; parties: unknown; terms: unknown }) =>
    api.post<{ document: string; downloadUrl: string }>('/legal/trust/generate', data),

  // UCC
  getUCCFilings: () =>
    api.get<UCCFiling[]>('/legal/ucc/filings'),

  createUCCFiling: (data: Partial<UCCFiling>) =>
    api.post<UCCFiling>('/legal/ucc/filings', data),

  // Alerts
  getAlerts: () =>
    api.get<LegalAlert[]>('/legal/alerts'),

  markAlertRead: (id: string) =>
    api.patch<void>(`/legal/alerts/${id}/read`),

  // Court Navigator
  getCourtInfo: (courtCode: string) =>
    api.get<{ name: string; address: string; phone: string; website: string; rules: string[] }>(`/legal/courts/${courtCode}`),
};
