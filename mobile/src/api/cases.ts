import { apiRequest } from './client';
import { LegalCase, CaseType, CaseStatus } from '@store/caseStore';

export interface CreateCaseRequest {
  title: string;
  type: CaseType;
  summary: string;
  opposingParty?: string;
  court?: string;
  deadlineDate?: string;
  priority: 'high' | 'medium' | 'low';
}

export interface MotionDraftRequest {
  caseId: string;
  motionType: string;
  keyArguments: string[];
  jurisdiction?: string;
}

export interface MotionDraftResponse {
  draftId: string;
  content: string;
  citations: string[];
  wordCount: number;
}

export interface CaseLawSearchRequest {
  query: string;
  jurisdiction?: string;
  dateRange?: { start: string; end: string };
  limit?: number;
}

export interface CaseLawResult {
  id: string;
  title: string;
  court: string;
  date: string;
  citation: string;
  summary: string;
  relevanceScore: number;
  url: string;
}

export const casesAPI = {
  list: (status?: CaseStatus) =>
    apiRequest<LegalCase[]>('get', '/cases', undefined, {
      params: { status },
    }),

  get: (caseId: string) =>
    apiRequest<LegalCase>('get', `/cases/${caseId}`),

  create: (data: CreateCaseRequest) =>
    apiRequest<LegalCase>('post', '/cases', data),

  update: (caseId: string, data: Partial<LegalCase>) =>
    apiRequest<LegalCase>('patch', `/cases/${caseId}`, data),

  delete: (caseId: string) =>
    apiRequest<void>('delete', `/cases/${caseId}`),

  draftMotion: (data: MotionDraftRequest) =>
    apiRequest<MotionDraftResponse>('post', '/cases/motion/draft', data),

  searchCaseLaw: (data: CaseLawSearchRequest) =>
    apiRequest<CaseLawResult[]>('post', '/legal/caselaw/search', data),

  getTimeline: (caseId: string) =>
    apiRequest<{ events: LegalCase['events'] }>('get', `/cases/${caseId}/timeline`),

  addNote: (caseId: string, note: string) =>
    apiRequest<void>('post', `/cases/${caseId}/notes`, { note }),
};
