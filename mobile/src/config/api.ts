// Auto-detects local vs production API
export const API_CONFIG = {
  baseUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  retries: 3,
};

export const FEATURES = {
  voiceEnabled: true,
  localLLM: process.env.EXPO_PUBLIC_LOCAL_LLM === 'true',
  biometricAuth: true,
  offlineMode: true,
};
