import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  TextInput as RNTextInput,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Eye, EyeOff, Mail, Lock, Fingerprint } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { AuthStackParamList } from '@navigation/types';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import { useAuth } from '@hooks/useAuth';
import { useBiometric } from '@hooks/useBiometric';
import { Validators } from '@utils/validation';
import LoadingOverlay from '@components/common/LoadingOverlay';

type Nav = NativeStackNavigationProp<AuthStackParamList, 'Login'>;

export default function LoginScreen() {
  const navigation = useNavigation<Nav>();
  const { signIn } = useAuth();
  const biometric = useBiometric();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const passwordRef = useRef<RNTextInput>(null);

  const validate = (): boolean => {
    const eErr = Validators.email(email);
    const pErr = Validators.password(password);
    setEmailError(eErr);
    setPasswordError(pErr);
    return !eErr && !pErr;
  };

  const handleLogin = async () => {
    if (!validate()) {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      return;
    }
    setIsLoading(true);
    try {
      await signIn({ email: email.trim().toLowerCase(), password });
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (error: any) {
      setIsLoading(false);
      Alert.alert(
        'Login Failed',
        error?.response?.data?.message ?? 'Invalid email or password. Please try again.',
      );
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    }
  };

  const handleBiometricLogin = async () => {
    const avail = await biometric.checkAvailability();
    if (!avail.isAvailable || !avail.isEnrolled) {
      Alert.alert('Biometric Not Available', 'Please set up Face ID or Touch ID in Settings.');
      return;
    }
    const success = await biometric.authenticate('Sign in to SintraPrime');
    if (success) {
      navigation.navigate('Biometric', {
        userId: 'stored-user-id',
        method: avail.biometricType === 'faceid' ? 'faceid' : 'touchid',
      });
    }
  };

  return (
    <LinearGradient
      colors={[Colors.navy[950], Colors.navy[900]]}
      style={styles.gradient}
    >
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView
          style={styles.kav}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* Logo */}
            <View style={styles.header}>
              <LinearGradient
                colors={[Colors.gold[400], Colors.gold[600]]}
                style={styles.logoBox}
              >
                <Text style={styles.logoText}>SP</Text>
              </LinearGradient>
              <Text style={styles.welcomeTitle}>Welcome back</Text>
              <Text style={styles.welcomeSub}>Sign in to your SintraPrime account</Text>
            </View>

            {/* Form */}
            <View style={styles.form}>
              {/* Email */}
              <View>
                <Text style={styles.fieldLabel}>Email Address</Text>
                <View style={[styles.inputRow, emailError ? styles.inputError : undefined]}>
                  <Mail size={18} color={Colors.textMuted} strokeWidth={1.5} />
                  <TextInput
                    style={styles.input}
                    value={email}
                    onChangeText={(v) => { setEmail(v); setEmailError(null); }}
                    placeholder="you@example.com"
                    placeholderTextColor={Colors.textMuted}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoCorrect={false}
                    returnKeyType="next"
                    onSubmitEditing={() => passwordRef.current?.focus()}
                    blurOnSubmit={false}
                  />
                </View>
                {emailError && <Text style={styles.errorText}>{emailError}</Text>}
              </View>

              {/* Password */}
              <View>
                <Text style={styles.fieldLabel}>Password</Text>
                <View style={[styles.inputRow, passwordError ? styles.inputError : undefined]}>
                  <Lock size={18} color={Colors.textMuted} strokeWidth={1.5} />
                  <TextInput
                    ref={passwordRef}
                    style={styles.input}
                    value={password}
                    onChangeText={(v) => { setPassword(v); setPasswordError(null); }}
                    placeholder="Enter your password"
                    placeholderTextColor={Colors.textMuted}
                    secureTextEntry={!showPassword}
                    returnKeyType="done"
                    onSubmitEditing={handleLogin}
                  />
                  <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                    {showPassword
                      ? <EyeOff size={18} color={Colors.textMuted} strokeWidth={1.5} />
                      : <Eye size={18} color={Colors.textMuted} strokeWidth={1.5} />
                    }
                  </TouchableOpacity>
                </View>
                {passwordError && <Text style={styles.errorText}>{passwordError}</Text>}
              </View>

              {/* Forgot */}
              <TouchableOpacity style={styles.forgotRow}>
                <Text style={styles.forgotText}>Forgot password?</Text>
              </TouchableOpacity>

              {/* Login CTA */}
              <TouchableOpacity
                onPress={handleLogin}
                activeOpacity={0.85}
                style={styles.loginBtnWrap}
              >
                <LinearGradient
                  colors={[Colors.gold[400], Colors.gold[600]]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.loginBtn}
                >
                  <Text style={styles.loginBtnText}>Sign In</Text>
                </LinearGradient>
              </TouchableOpacity>

              {/* Divider */}
              <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>or</Text>
                <View style={styles.dividerLine} />
              </View>

              {/* Biometric */}
              <TouchableOpacity
                onPress={handleBiometricLogin}
                activeOpacity={0.85}
                style={styles.biometricBtn}
              >
                <Fingerprint size={22} color={Colors.gold[500]} strokeWidth={1.5} />
                <Text style={styles.biometricText}>
                  Sign in with Face ID / Touch ID
                </Text>
              </TouchableOpacity>
            </View>

            {/* Footer */}
            <View style={styles.footer}>
              <Text style={styles.footerText}>
                🔒 Your data is encrypted end-to-end
              </Text>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>

      <LoadingOverlay visible={isLoading} message="Signing you in..." />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: { flex: 1 },
  safe: { flex: 1 },
  kav: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing['2xl'],
  },
  header: {
    alignItems: 'center',
    paddingTop: Spacing['3xl'],
    paddingBottom: Spacing['2xl'],
    gap: Spacing.sm,
  },
  logoBox: {
    width: 72,
    height: 72,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
    ...Shadow.gold,
  },
  logoText: {
    fontSize: 32,
    fontWeight: '800',
    color: Colors.navy[900],
    letterSpacing: -1,
  },
  welcomeTitle: {
    ...Typography.headlineMedium,
    color: Colors.textPrimary,
  },
  welcomeSub: {
    ...Typography.bodyMedium,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  form: {
    gap: Spacing.base,
  },
  fieldLabel: {
    ...Typography.labelMedium,
    color: Colors.textSecondary,
    marginBottom: Spacing.xs,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    paddingHorizontal: Spacing.base,
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    height: 52,
  },
  inputError: {
    borderColor: Colors.error,
  },
  input: {
    flex: 1,
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    height: '100%',
  },
  errorText: {
    ...Typography.bodySmall,
    color: Colors.error,
    marginTop: Spacing.xs,
  },
  forgotRow: {
    alignItems: 'flex-end',
  },
  forgotText: {
    ...Typography.labelMedium,
    color: Colors.gold[500],
  },
  loginBtnWrap: {
    borderRadius: BorderRadius.full,
    overflow: 'hidden',
    marginTop: Spacing.sm,
    ...Shadow.gold,
  },
  loginBtn: {
    height: 54,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: BorderRadius.full,
  },
  loginBtnText: {
    ...Typography.titleMedium,
    color: Colors.navy[900],
    fontWeight: '700',
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.border,
  },
  dividerText: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  biometricBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    borderWidth: 1.5,
    borderColor: Colors.gold[500],
    borderRadius: BorderRadius.full,
    height: 54,
  },
  biometricText: {
    ...Typography.labelLarge,
    color: Colors.gold[500],
  },
  footer: {
    alignItems: 'center',
    marginTop: Spacing['2xl'],
  },
  footerText: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
});
