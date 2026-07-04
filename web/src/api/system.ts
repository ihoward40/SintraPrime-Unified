/**
 * System Health API client
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({ baseURL: API_BASE, timeout: 15000 });

export interface SystemHealth {
  overall: string;
  timestamp: string;
  subsystems: Record<string, {
    status: string;
    [key: string]: unknown;
  }>;
}

export const systemApi = {
  getHealth: async (): Promise<SystemHealth> => {
    const { data } = await client.get('/api/system/health');
    return data;
  },
};

export default systemApi;