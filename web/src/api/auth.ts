import { apiClient } from './client';

export interface LoginRequest {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  requires_mfa: boolean;
  mfa_challenge_token?: string;
  user_id: string;
  role: string;
  tenant_id: string;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface FirstRunSetupStatus {
  available: boolean;
}

export interface FirstRunSetupRequest {
  owner_name: string;
  email: string;
  password: string;
  organization_name: string;
}

const storeAccessToken = (accessToken: string, expiresIn: number): void => {
  localStorage.setItem('sintraprime_token', accessToken);
  const expiresAt = Date.now() + expiresIn * 1000;
  localStorage.setItem('sintraprime_token_expires_at', expiresAt.toString());
};

/**
 * Authenticate with email + password.
 * On success, stores access token in localStorage. The refresh token is
 * delivered as an httpOnly cookie by the backend (requires withCredentials).
 */
export const login = async (credentials: LoginRequest): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
  const data = response.data;
  if (data.access_token) {
    storeAccessToken(data.access_token, data.expires_in);
  }
  return data;
};

/**
 * Refresh the access token using the httpOnly refresh cookie.
 * The cookie is sent automatically because apiClient uses withCredentials.
 */
export const refreshAccessToken = async (): Promise<RefreshResponse> => {
  const response = await apiClient.post<RefreshResponse>('/auth/refresh', {});
  const data = response.data;
  if (data.access_token) {
    storeAccessToken(data.access_token, data.expires_in);
  }
  return data;
};


export const getFirstRunSetupStatus = async (): Promise<FirstRunSetupStatus> => {
  const response = await apiClient.get<FirstRunSetupStatus>('/auth/setup/status');
  return response.data;
};

export const completeFirstRunSetup = async (payload: FirstRunSetupRequest): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/setup', payload);
  const data = response.data;
  if (data.access_token) {
    storeAccessToken(data.access_token, data.expires_in);
  }
  return data;
};

export const logout = (): void => {
  localStorage.removeItem('sintraprime_token');
  localStorage.removeItem('sintraprime_token_expires_at');
  window.location.href = '/login';
};

export const hasValidToken = (): boolean => {
  const token = localStorage.getItem('sintraprime_token');
  const expiresAt = localStorage.getItem('sintraprime_token_expires_at');
  if (!token || !expiresAt) return false;
  return Date.now() < parseInt(expiresAt, 10);
};

export default {
  login,
  refreshAccessToken,
  getFirstRunSetupStatus,
  completeFirstRunSetup,
  logout,
  hasValidToken,
};
