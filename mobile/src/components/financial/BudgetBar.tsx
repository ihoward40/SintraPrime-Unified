import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withTiming, Easing } from 'react-native-reanimated';
import { BudgetCategory } from '@store/financialStore';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { formatCurrency } from '@utils/formatting';

interface BudgetBarProps {
  category: BudgetCategory;
}

export default function BudgetBar({ category }: BudgetBarProps) {
  const pct = Math.min(category.spent / category.budgeted, 1);
  const isOver = category.spent > category.budgeted;
  const barWidth = useSharedValue(0);

  useEffect(() => {
    barWidth.value = withTiming(pct, { duration: 1000, easing: Easing.out(Easing.cubic) });
  }, [pct]);

  const animatedStyle = useAnimatedStyle(() => ({
    width: `${barWidth.value * 100}%` as any,
  }));

  const barColor = isOver ? Colors.error : pct > 0.8 ? Colors.warning : category.color;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.name}>{category.name}</Text>
        <View style={styles.amounts}>
          <Text style={[styles.spent, isOver && styles.spentOver]}>
            {formatCurrency(category.spent, 'USD', { maximumFractionDigits: 0 })}
          </Text>
          <Text style={styles.separator}>/</Text>
          <Text style={styles.budgeted}>
            {formatCurrency(category.budgeted, 'USD', { maximumFractionDigits: 0 })}
          </Text>
        </View>
      </View>
      <View style={styles.track}>
        <Animated.View
          style={[styles.fill, { backgroundColor: barColor }, animatedStyle]}
        />
      </View>
      <Text style={[styles.pctText, isOver && styles.pctOver]}>
        {isOver
          ? `${formatCurrency(category.spent - category.budgeted, 'USD', { maximumFractionDigits: 0 })} over budget`
          : `${Math.round(pct * 100)}% used`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.xs,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  name: {
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    fontWeight: '500',
  },
  amounts: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  spent: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  spentOver: {
    color: Colors.error,
  },
  separator: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  budgeted: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  track: {
    height: 8,
    backgroundColor: Colors.border,
    borderRadius: BorderRadius.full,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: BorderRadius.full,
  },
  pctText: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
  },
  pctOver: {
    color: Colors.error,
  },
});
