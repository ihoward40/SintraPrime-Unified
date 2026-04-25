import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import * as SecureStore from 'expo-secure-store';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'https://api.sintraprime.com/v1';
const TOKEN_KEY = 'sintraprime_auth_token';

let apiClient: AxiosInstance;

export const createAPIClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-Client-Platform': 'mobile',
      'X-Client-Version': '1.0.0',
    },
  });

  // Request interceptor — attach token
  client.interceptors.request.use(
    async (config) => {
      const token = await SecureStore.getItemAsync(TOKEN_KEY);
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error),
  );

  // Response interceptor — handle 401
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error) => {
      if (error.response?.status === 401) {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        // Trigger logout in store — handled by app state
      }
      return Promise.reject(error);
    },
  );

  return client;
};

export const getAPIClient = (): AxiosInstance => {
  if (!apiClient) {
    apiClient = createAPIClient();
  }
  return apiClient;
};

// Generic request helper
export async function apiRequest<T>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  path: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const client = getAPIClient();
  const response = await client[method]<T>(path, data, config);
  return response.data;
}
