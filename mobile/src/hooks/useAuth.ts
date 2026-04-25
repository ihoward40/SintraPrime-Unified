import { useCallback } from 'react';
import { useAuthStore } from '@store/authStore';
import { authAPI, LoginRequest } from '@api/auth';

export function useAuth() {
  const { user, token, isAuthenticated, login, logout, loadStoredAuth } = useAuthStore();

  const signIn = useCallback(
    async (credentials: LoginRequest) => {
      const response = await authAPI.login(credentials);
      await login(response.token, response.user);
      return response.user;
    },
    [login],
  );

  const signOut = useCallback(async () => {
    try {
      await authAPI.logout();
    } catch {
      // Ignore logout errors
    }
    await logout();
  }, [logout]);

  return {
    user,
    token,
    isAuthenticated,
    signIn,
    signOut,
    loadStoredAuth,
  };
}
