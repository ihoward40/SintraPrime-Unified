import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

// Base API configuration
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_VERSION = 'v1';

export interface APIResponse<T = unknown> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
    hasMore?: boolean;
  };
}

export interface APIError {
  message: string;
  code?: string;
  details?: Record<string, string[]>;
  status: number;
}

// Create axios instance
const createAPIClient = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: `${BASE_URL}/api/${API_VERSION}`,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });

  // Request interceptor - attach auth token
  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('sintraprime_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      // Add request ID for tracing
      config.headers['X-Request-ID'] = crypto.randomUUID();
      config.headers['X-Client-Version'] = '1.0.0';
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor - normalize responses
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
      
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        // Attempt token refresh
        try {
          const refreshToken = localStorage.getItem('sintraprime_refresh_token');
          if (refreshToken) {
            const response = await axios.post(`${BASE_URL}/api/${API_VERSION}/auth/refresh`, {
              refresh_token: refreshToken,
            });
            const { access_token } = response.data;
            localStorage.setItem('sintraprime_token', access_token);
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            return instance(originalRequest);
          }
        } catch {
          localStorage.removeItem('sintraprime_token');
          localStorage.removeItem('sintraprime_refresh_token');
          window.location.href = '/login';
        }
      }

      const apiError: APIError = {
        message: (error.response?.data as { message?: string })?.message || error.message || 'An error occurred',
        code: (error.response?.data as { code?: string })?.code,
        details: (error.response?.data as { details?: Record<string, string[]> })?.details,
        status: error.response?.status || 500,
      };

      return Promise.reject(apiError);
    }
  );

  return instance;
};

export const apiClient = createAPIClient();

// Convenience methods
export const api = {
  get: <T>(url: string, params?: Record<string, unknown>) =>
    apiClient.get<APIResponse<T>>(url, { params }).then((r) => r.data),

  post: <T>(url: string, data?: unknown) =>
    apiClient.post<APIResponse<T>>(url, data).then((r) => r.data),

  put: <T>(url: string, data?: unknown) =>
    apiClient.put<APIResponse<T>>(url, data).then((r) => r.data),

  patch: <T>(url: string, data?: unknown) =>
    apiClient.patch<APIResponse<T>>(url, data).then((r) => r.data),

  delete: <T>(url: string) =>
    apiClient.delete<APIResponse<T>>(url).then((r) => r.data),

  upload: <T>(url: string, formData: FormData) =>
    apiClient.post<APIResponse<T>>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
};

export default api;
