import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react-native';

interface StatBadgeProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  accent?: boolean;
  style?: ViewStyle;
  size?: 'sm' | 'md' | 'lg';
}

export default function StatBadge({
  label,
  value,
  trend,
  trendValue,
  accent = false,
  style,
  size = 'md',
}: StatBadgeProps) {
  const getTrendColor = () => {
    if (trend === 'up') return Colors.success;
    if (trend === 'down') return Colors.error;
    return Colors.textMuted;
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <View style={[styles.container, style]}>
      <Text style={[styles.label, size === 'sm' && styles.labelSm]}>{label}</Text>
      <Text
        style={[
          styles.value,
          size === 'lg' && styles.valueLg,
          size === 'sm' && styles.valueSm,
          accent && styles.valueAccent,
        ]}
      >
        {value}
      </Text>
      {trend && (
        <View style={styles.trend}>
          <TrendIcon
            size={12}
            color={getTrendColor()}
            strokeWidth={2}
          />
          {trendValue && (
            <Text style={[styles.trendText, { color: getTrendColor() }]}>
              {trendValue}
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  label: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
    marginBottom: Spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  labelSm: {
    fontSize: 10,
  },
  value: {
    ...Typography.titleLarge,
    color: Colors.textPrimary,
  },
  valueLg: {
    ...Typography.headlineMedium,
  },
  valueSm: {
    ...Typography.titleMedium,
  },
  valueAccent: {
    color: Colors.gold[500],
  },
  trend: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginTop: 2,
  },
  trendText: {
    ...Typography.labelSmall,
    fontSize: 11,
  },
});
