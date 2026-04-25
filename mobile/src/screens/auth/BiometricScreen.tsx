import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { Fingerprint, ScanFace, Shield } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { AuthStackParamList } from '@navigation/types';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, Shadow } from '@theme/spacing';
import { useBiometric } from '@hooks/useBiometric';
import { useAuthStore } from '@store/authStore';

type RouteType = RouteProp<AuthStackParamList, 'Biometric'>;

export default function BiometricScreen() {
  const navigation = useNavigation();
  const route = useRoute<RouteType>();
  const { method } = route.params;
  const biometric = useBiometric();
  const { login } = useAuthStore();
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const Icon = method === 'faceid' ? ScanFace : Fingerprint;
  const label = method === 'faceid' ? 'Face ID' : 'Touch ID';

  const authenticate = async () => {
    setIsAuthenticating(true);
    const success = await biometric.authenticate(`Use ${label} to sign in`);
    setIsAuthenticating(false);

    if (success) {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      // In production, exchange biometric token for auth token
      // For now, navigate back
      navigation.goBack();
    } else {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      Alert.alert('Authentication Failed', `${label} authentication was not successful.`);
    }
  };

  useEffect(() => {
    // Auto-trigger biometric on mount
    const timer = setTimeout(authenticate, 500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <LinearGradient
      colors={[Colors.navy[950], Colors.navy[900]]}
      style={styles.gradient}
    >
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          {/* Icon */}
          <View style={styles.iconContainer}>
            <View style={styles.iconRing}>
              <Icon
                size={56}
                color={Colors.gold[500]}
                strokeWidth={1}
              />
            </View>
            <View style={styles.shieldBadge}>
              <Shield size={16} color={Colors.success} fill={Colors.success} strokeWidth={0} />
            </View>
          </View>

          <Text style={styles.title}>Authenticate with {label}</Text>
          <Text style={styles.subtitle}>
            Use {label} for quick and secure access to your SintraPrime account
          </Text>

          {/* Retry button */}
          <TouchableOpacity
            onPress={authenticate}
            activeOpacity={0.85}
            style={styles.retryBtn}
            disabled={isAuthenticating}
          >
            <LinearGradient
              colors={[Colors.gold[400], Colors.gold[600]]}
              style={styles.retryGradient}
            >
              <Icon size={18} color={Colors.navy[900]} strokeWidth={1.5} />
              <Text style={styles.retryText}>
                {isAuthenticating ? 'Authenticating...' : `Use ${label}`}
              </Text>
            </LinearGradient>
          </TouchableOpacity>

          {/* Fallback */}
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.fallback}>
            <Text style={styles.fallbackText}>Use password instead</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: { flex: 1 },
  safe: { flex: 1 },
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing['2xl'],
    gap: Spacing.base,
  },
  iconContainer: {
    position: 'relative',
    marginBottom: Spacing.lg,
  },
  iconRing: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: Colors.surface,
    borderWidth: 2,
    borderColor: Colors.gold[500] + '60',
    alignItems: 'center',
    justifyContent: 'center',
    ...Shadow.gold,
  },
  shieldBadge: {
    position: 'absolute',
    bottom: 4,
    right: 4,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.navy[900],
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.navy[900],
  },
  title: {
    ...Typography.headlineSmall,
    color: Colors.textPrimary,
    textAlign: 'center',
  },
  subtitle: {
    ...Typography.bodyMedium,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
  },
  retryBtn: {
    width: '100%',
    borderRadius: 100,
    overflow: 'hidden',
    marginTop: Spacing.xl,
    ...Shadow.gold,
  },
  retryGradient: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  retryText: {
    ...Typography.titleSmall,
    color: Colors.navy[900],
    fontWeight: '700',
  },
  fallback: {
    marginTop: Spacing.base,
    padding: Spacing.md,
  },
  fallbackText: {
    ...Typography.labelLarge,
    color: Colors.gold[500],
  },
});
