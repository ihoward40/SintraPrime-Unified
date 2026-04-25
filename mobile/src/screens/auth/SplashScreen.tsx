import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  withSequence,
  withSpring,
  Easing,
  runOnJS,
} from 'react-native-reanimated';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthStackParamList } from '@navigation/types';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { useAuthStore } from '@store/authStore';

const { width, height } = Dimensions.get('window');

type Nav = NativeStackNavigationProp<AuthStackParamList, 'Splash'>;

export default function SplashScreen() {
  const navigation = useNavigation<Nav>();
  const { loadStoredAuth, isAuthenticated } = useAuthStore();

  const logoOpacity = useSharedValue(0);
  const logoScale = useSharedValue(0.6);
  const taglineOpacity = useSharedValue(0);
  const taglineY = useSharedValue(20);
  const ringScale = useSharedValue(0);
  const ringOpacity = useSharedValue(0);

  const navigate = () => {
    navigation.replace('Login');
  };

  useEffect(() => {
    const init = async () => {
      await loadStoredAuth();
    };
    init();

    // Logo entrance
    logoOpacity.value = withDelay(300, withTiming(1, { duration: 700 }));
    logoScale.value = withDelay(300, withSpring(1, { damping: 12, stiffness: 90 }));

    // Ring pulse
    ringScale.value = withDelay(
      600,
      withSequence(withTiming(1.4, { duration: 800 }), withTiming(0, { duration: 400 })),
    );
    ringOpacity.value = withDelay(
      600,
      withSequence(
        withTiming(0.4, { duration: 400 }),
        withTiming(0, { duration: 400 }),
      ),
    );

    // Tagline
    taglineOpacity.value = withDelay(900, withTiming(1, { duration: 600 }));
    taglineY.value = withDelay(900, withTiming(0, { duration: 600, easing: Easing.out(Easing.cubic) }));

    // Navigate after animation
    const timer = setTimeout(() => runOnJS(navigate)(), 2400);
    return () => clearTimeout(timer);
  }, []);

  const logoStyle = useAnimatedStyle(() => ({
    opacity: logoOpacity.value,
    transform: [{ scale: logoScale.value }],
  }));

  const taglineStyle = useAnimatedStyle(() => ({
    opacity: taglineOpacity.value,
    transform: [{ translateY: taglineY.value }],
  }));

  const ringStyle = useAnimatedStyle(() => ({
    opacity: ringOpacity.value,
    transform: [{ scale: ringScale.value }],
  }));

  return (
    <LinearGradient
      colors={[Colors.navy[950], Colors.navy[900], Colors.navy[800]]}
      style={styles.container}
    >
      {/* Ring pulse */}
      <Animated.View style={[styles.ring, ringStyle]} />

      {/* Logo container */}
      <Animated.View style={[styles.logoContainer, logoStyle]}>
        {/* SP emblem */}
        <View style={styles.emblem}>
          <LinearGradient
            colors={[Colors.gold[400], Colors.gold[600]]}
            style={styles.emblemGradient}
          >
            <Text style={styles.emblemText}>SP</Text>
          </LinearGradient>
        </View>

        {/* Brand name */}
        <Text style={styles.brandName}>SintraPrime</Text>
        <Text style={styles.brandUnified}>UNIFIED</Text>
      </Animated.View>

      {/* Tagline */}
      <Animated.View style={[styles.taglineContainer, taglineStyle]}>
        <Text style={styles.tagline}>Your AI Law Firm &amp; Financial Advisor</Text>
        <View style={styles.goldDivider} />
        <Text style={styles.taglineSub}>Available 24/7 · Everywhere</Text>
      </Animated.View>

      {/* Bottom branding */}
      <View style={styles.bottom}>
        <Text style={styles.bottomText}>Powered by SintraPrime Intelligence™</Text>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ring: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    borderWidth: 1,
    borderColor: Colors.gold[500],
  },
  logoContainer: {
    alignItems: 'center',
    gap: 12,
  },
  emblem: {
    shadowColor: Colors.gold[500],
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 24,
    elevation: 20,
  },
  emblemGradient: {
    width: 96,
    height: 96,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emblemText: {
    fontSize: 42,
    fontWeight: '800',
    color: Colors.navy[900],
    letterSpacing: -1,
  },
  brandName: {
    fontSize: 34,
    fontWeight: '700',
    color: Colors.textPrimary,
    letterSpacing: -0.5,
  },
  brandUnified: {
    ...Typography.labelLarge,
    color: Colors.gold[500],
    letterSpacing: 8,
    marginTop: -6,
  },
  taglineContainer: {
    alignItems: 'center',
    marginTop: 48,
    gap: 12,
  },
  tagline: {
    ...Typography.titleSmall,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  goldDivider: {
    width: 48,
    height: 2,
    backgroundColor: Colors.gold[500],
    borderRadius: 1,
  },
  taglineSub: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  bottom: {
    position: 'absolute',
    bottom: 48,
  },
  bottomText: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
    textAlign: 'center',
  },
});
