import * as SecureStore from 'expo-secure-store';

// Secure storage wrappers
export const SecureStorage = {
  set: async (key: string, value: string): Promise<void> => {
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },

  get: async (key: string): Promise<string | null> => {
    return SecureStore.getItemAsync(key);
  },

  delete: async (key: string): Promise<void> => {
    await SecureStore.deleteItemAsync(key);
  },

  setObject: async <T>(key: string, value: T): Promise<void> => {
    await SecureStore.setItemAsync(key, JSON.stringify(value), {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },

  getObject: async <T>(key: string): Promise<T | null> => {
    const value = await SecureStore.getItemAsync(key);
    if (!value) return null;
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  },
};

// Keys registry
export const SecureKeys = {
  AUTH_TOKEN: 'sp_auth_token',
  REFRESH_TOKEN: 'sp_refresh_token',
  USER_DATA: 'sp_user_data',
  BIOMETRIC_TOKEN: 'sp_biometric_token',
  PIN_HASH: 'sp_pin_hash',
  DEVICE_ID: 'sp_device_id',
} as const;
