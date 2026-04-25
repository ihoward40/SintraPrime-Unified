import React, { ReactNode } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  TouchableOpacityProps,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { Colors } from '@theme/colors';
import { Shadow, BorderRadius, Spacing } from '@theme/spacing';

interface GoldCardProps extends TouchableOpacityProps {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'gold' | 'outline';
  style?: ViewStyle;
  onPress?: () => void;
  animated?: boolean;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export default function GoldCard({
  children,
  variant = 'default',
  style,
  onPress,
  animated = true,
  ...props
}: GoldCardProps) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePressIn = () => {
    if (animated) scale.value = withSpring(0.97, { damping: 15, stiffness: 300 });
  };

  const handlePressOut = () => {
    if (animated) scale.value = withSpring(1, { damping: 15, stiffness: 300 });
  };

  const content = (
    <View style={[styles.inner, style]}>{children}</View>
  );

  if (variant === 'gold') {
    return (
      <AnimatedTouchable
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.9}
        style={[animatedStyle, styles.shadow]}
        {...props}
      >
        <LinearGradient
          colors={[Colors.gold[400], Colors.gold[600]]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.container, styles.goldContainer]}
        >
          {content}
        </LinearGradient>
      </AnimatedTouchable>
    );
  }

  if (variant === 'outline') {
    return (
      <AnimatedTouchable
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.9}
        style={[animatedStyle, styles.outlineContainer, style]}
        {...props}
      >
        {children}
      </AnimatedTouchable>
    );
  }

  return (
    <AnimatedTouchable
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      activeOpacity={onPress ? 0.85 : 1}
      style={[
        animatedStyle,
        styles.container,
        variant === 'elevated' && styles.elevated,
        style,
      ]}
      {...props}
    >
      {children}
    </AnimatedTouchable>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.md,
  },
  elevated: {
    backgroundColor: Colors.surfaceElevated,
    borderColor: Colors.borderLight,
    ...Shadow.lg,
  },
  goldContainer: {
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 0,
  },
  outlineContainer: {
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1.5,
    borderColor: Colors.gold[500],
    backgroundColor: 'transparent',
  },
  inner: {
    flex: 1,
  },
  shadow: {
    ...Shadow.gold,
  },
});
