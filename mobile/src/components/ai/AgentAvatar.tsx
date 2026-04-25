import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Bot } from 'lucide-react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { BorderRadius } from '@theme/spacing';

interface AgentAvatarProps {
  name: string;
  specialty?: string;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

const SIZE_MAP = {
  sm: { container: 36, icon: 16, text: 10 },
  md: { container: 52, icon: 22, text: 13 },
  lg: { container: 72, icon: 32, text: 16 },
};

export default function AgentAvatar({
  name,
  specialty,
  size = 'md',
  animated: isAnimated = false,
}: AgentAvatarProps) {
  const glow = useSharedValue(0.4);
  const dim = SIZE_MAP[size];

  if (isAnimated) {
    glow.value = withRepeat(withTiming(1, { duration: 1500 }), -1, true);
  }

  const glowStyle = useAnimatedStyle(() => ({
    shadowOpacity: isAnimated ? glow.value : 0.4,
  }));

  return (
    <Animated.View style={[styles.wrapper, glowStyle, { shadowColor: Colors.gold[500] }]}>
      <LinearGradient
        colors={[Colors.navy[700], Colors.navy[900]]}
        style={[
          styles.container,
          {
            width: dim.container,
            height: dim.container,
            borderRadius: dim.container / 2,
          },
        ]}
      >
        <Bot size={dim.icon} color={Colors.gold[400]} strokeWidth={1.5} />
      </LinearGradient>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 12,
    elevation: 8,
  },
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: Colors.gold[500] + '80',
  },
});
