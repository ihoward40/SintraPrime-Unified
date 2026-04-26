import { useState, useCallback } from 'react';
import { API_CONFIG } from '../config/api';

interface SintraQuery {
  question: string;
  jurisdiction?: string;
  category?: 'trust' | 'legal' | 'banking' | 'federal';
}

interface TrustData {
  [key: string]: unknown;
}

interface APIResponse {
  [key: string]: unknown;
}

export function useSintraAPI() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = useCallback(async (query: SintraQuery): Promise<APIResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/rag/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(query),
      });
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const trustAnalysis = useCallback(async (trustData: TrustData): Promise<APIResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/trust/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trustData),
      });
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getLegalCategories = useCallback(async (): Promise<string[]> => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/categories`);
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const data = await response.json();
      return data.categories || [];
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return [];
    }
  }, []);

  const getJurisdictions = useCallback(async (): Promise<string[]> => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/jurisdictions`);
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const data = await response.json();
      return data.jurisdictions || [];
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return [];
    }
  }, []);

  return { ask, trustAnalysis, getLegalCategories, getJurisdictions, loading, error };
}
