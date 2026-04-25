import { apiRequest } from './client';
import { User } from '@store/authStore';

export interface LoginRequest {
  email: string;
  password: string;
  deviceId?: string;
}

export interface LoginResponse {
  token: string;
  refreshToken: string;
  expiresAt: string;
  user: User;
}

export interface BiometricAuthRequest {
  userId: string;
  biometricToken: string;
  deviceId: string;
}

export const authAPI = {
  login: (data: LoginRequest) =>
    apiRequest<LoginResponse>('post', '/auth/login', data),

  logout: () =>
    apiRequest<void>('post', '/auth/logout'),

  refreshToken: (refreshToken: string) =>
    apiRequest<{ token: string; expiresAt: string }>('post', '/auth/refresh', {
      refreshToken,
    }),

  biometricAuth: (data: BiometricAuthRequest) =>
    apiRequest<LoginResponse>('post', '/auth/biometric', data),

  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>('post', '/auth/forgot-password', { email }),

  resetPassword: (token: string, password: string) =>
    apiRequest<{ message: string }>('post', '/auth/reset-password', {
      token,
      password,
    }),

  getMe: () =>
    apiRequest<User>('get', '/auth/me'),

  updateProfile: (data: Partial<User>) =>
    apiRequest<User>('patch', '/auth/me', data),
};
