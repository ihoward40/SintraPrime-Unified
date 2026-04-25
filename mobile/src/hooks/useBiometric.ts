import { useState, useCallback } from 'react';
import * as LocalAuthentication from 'expo-local-authentication';

export type BiometricType = 'faceid' | 'touchid' | 'none';

export interface BiometricState {
  isAvailable: boolean;
  biometricType: BiometricType;
  isEnrolled: boolean;
}

export function useBiometric() {
  const [state, setState] = useState<BiometricState>({
    isAvailable: false,
    biometricType: 'none',
    isEnrolled: false,
  });

  const checkAvailability = useCallback(async (): Promise<BiometricState> => {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();

    let biometricType: BiometricType = 'none';
    if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
      biometricType = 'faceid';
    } else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
      biometricType = 'touchid';
    }

    const result: BiometricState = {
      isAvailable: hasHardware,
      biometricType,
      isEnrolled,
    };
    setState(result);
    return result;
  }, []);

  const authenticate = useCallback(
    async (promptMessage = 'Authenticate to continue'): Promise<boolean> => {
      try {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage,
          cancelLabel: 'Cancel',
          disableDeviceFallback: false,
          fallbackLabel: 'Use Passcode',
        });
        return result.success;
      } catch {
        return false;
      }
    },
    [],
  );

  return {
    ...state,
    checkAvailability,
    authenticate,
  };
}
