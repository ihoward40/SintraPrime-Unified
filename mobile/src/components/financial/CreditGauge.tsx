import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle, Path, Defs, LinearGradient, Stop, G } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  Easing,
  interpolate,
} from 'react-native-reanimated';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { getCreditScoreColor, getCreditScoreLabel } from '@utils/formatting';

const AnimatedPath = Animated.createAnimatedComponent(Path);

interface CreditGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

const MIN_SCORE = 300;
const MAX_SCORE = 850;
const ARC_ANGLE = 220; // degrees of arc

function scoreToPercent(score: number): number {
  return (score - MIN_SCORE) / (MAX_SCORE - MIN_SCORE);
}

function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angleDeg: number,
): { x: number; y: number } {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? '0' : '1';
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export default function CreditGauge({
  score,
  size = 220,
  strokeWidth = 18,
}: CreditGaugeProps) {
  const progress = useSharedValue(0);
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - strokeWidth) / 2;

  const startAngle = 90 + (360 - ARC_ANGLE) / 2;
  const endAngle = startAngle + ARC_ANGLE;

  useEffect(() => {
    progress.value = withTiming(scoreToPercent(score), {
      duration: 1500,
      easing: Easing.out(Easing.cubic),
    });
  }, [score]);

  const animatedProps = useAnimatedProps(() => {
    const currentAngle = startAngle + progress.value * ARC_ANGLE;
    return {
      d: describeArc(cx, cy, r, startAngle, currentAngle),
    };
  });

  const scoreColor = getCreditScoreColor(score);
  const scoreLabel = getCreditScoreLabel(score);
  const trackPath = describeArc(cx, cy, r, startAngle, endAngle);

  return (
    <View style={styles.container}>
      <Svg width={size} height={size}>
        <Defs>
          <LinearGradient id="gaugeGradient" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={Colors.error} stopOpacity="1" />
            <Stop offset="0.3" stopColor={Colors.warning} stopOpacity="1" />
            <Stop offset="0.6" stopColor={Colors.gold[500]} stopOpacity="1" />
            <Stop offset="1" stopColor={Colors.success} stopOpacity="1" />
          </LinearGradient>
        </Defs>

        {/* Track */}
        <Path
          d={trackPath}
          stroke={Colors.border}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
        />

        {/* Progress */}
        <AnimatedPath
          animatedProps={animatedProps}
          stroke="url(#gaugeGradient)"
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
        />
      </Svg>

      {/* Center text */}
      <View style={[styles.centerText, { width: size, height: size }]}>
        <Text style={[styles.score, { color: scoreColor }]}>{score}</Text>
        <Text style={styles.label}>{scoreLabel}</Text>
        <Text style={styles.range}>{MIN_SCORE}–{MAX_SCORE}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  centerText: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  score: {
    fontSize: 52,
    fontWeight: '800',
    letterSpacing: -2,
  },
  label: {
    ...Typography.titleSmall,
    color: Colors.textSecondary,
    marginTop: -4,
  },
  range: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
    marginTop: 4,
  },
});
