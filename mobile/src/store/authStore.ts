import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'client' | 'attorney' | 'advisor';
  avatarUrl?: string;
  subscriptionTier: 'basic' | 'pro' | 'elite';
  biometricEnabled: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  biometricEnabled: boolean;

  // Actions
  setUser: (user: User) => void;
  setToken: (token: string) => void;
  login: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
  loadStoredAuth: () => Promise<void>;
  enableBiometric: () => void;
  disableBiometric: () => void;
}

const TOKEN_KEY = 'sintraprime_auth_token';
const USER_KEY = 'sintraprime_user';

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  biometricEnabled: false,

  setUser: (user) => set({ user }),
  setToken: (token) => set({ token }),

  login: async (token, user) => {
    try {
      await SecureStore.setItemAsync(TOKEN_KEY, token);
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
      set({ user, token, isAuthenticated: true });
    } catch (error) {
      console.error('Failed to save auth:', error);
    }
  },

  logout: async () => {
    try {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      await SecureStore.deleteItemAsync(USER_KEY);
    } catch (error) {
      console.error('Failed to clear auth:', error);
    }
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadStoredAuth: async () => {
    try {
      const [token, userJson] = await Promise.all([
        SecureStore.getItemAsync(TOKEN_KEY),
        SecureStore.getItemAsync(USER_KEY),
      ]);
      if (token && userJson) {
        const user = JSON.parse(userJson) as User;
        set({ token, user, isAuthenticated: true, biometricEnabled: user.biometricEnabled });
      }
    } catch (error) {
      console.error('Failed to load auth:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  enableBiometric: () => {
    set({ biometricEnabled: true });
    const user = get().user;
    if (user) {
      const updatedUser = { ...user, biometricEnabled: true };
      set({ user: updatedUser });
      SecureStore.setItemAsync(USER_KEY, JSON.stringify(updatedUser));
    }
  },

  disableBiometric: () => {
    set({ biometricEnabled: false });
    const user = get().user;
    if (user) {
      const updatedUser = { ...user, biometricEnabled: false };
      set({ user: updatedUser });
      SecureStore.setItemAsync(USER_KEY, JSON.stringify(updatedUser));
    }
  },
}));
