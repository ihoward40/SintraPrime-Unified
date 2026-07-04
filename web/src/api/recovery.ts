/**
 * Recovery API client — connects frontend to FastAPI recovery endpoints
 * No auth required for dashboard and case listing
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export interface DashboardStats {
  status: string;
  tenant: string;
  cases: {
    total: number;
    high_priority: number;
    medium_priority: number;
    evidence_intake: number;
  };
  evidence: {
    total_items: number;
    total_receipts: number;
  };
  case_readiness: Array<{
    case_id: string;
    overall: number;
    grade: string;
    repository: number;
    evidence: number;
    legal: number;
    procedural: number;
  }>;
  high_priority_cases: Array<{
    case_id: string;
    name: string;
    status: string;
  }>;
  external_action: string;
  platform_version: string;
  evidence_kernel: string;
  timestamp: string;
}

export interface RecoveryCase {
  case_id: string;
  case_name: string;
  category: string;
  priority: string;
  status: string;
  external_action: string;
  approval_required: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CaseListResponse {
  count: number;
  cases: RecoveryCase[];
  external_action: string;
  approval_required_before: string[];
}

export const recoveryApi = {
  getDashboard: async (): Promise<DashboardStats> => {
    const { data } = await client.get('/api/recovery/dashboard');
    return data;
  },

  getCases: async (): Promise<CaseListResponse> => {
    const { data } = await client.get('/api/recovery/cases');
    return data;
  },

  getHealth: async () => {
    const { data } = await client.get('/api/recovery/health');
    return data;
  },

  getCasePacket: async (caseId: string) => {
    const { data } = await client.get(`/api/recovery/case-packet/${caseId}`);
    return data;
  },

  getCasePacketMarkdown: async (caseId: string) => {
    const { data } = await client.get(`/api/recovery/case-packet/${caseId}/markdown`);
    return data;
  },

  getExportJson: async () => {
    const { data } = await client.get('/api/recovery/export/json');
    return data;
  },
};

export default recoveryApi;