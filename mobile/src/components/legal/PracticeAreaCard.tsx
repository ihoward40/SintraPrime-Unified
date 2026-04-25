import React, { ReactNode } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ChevronRight } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';

interface PracticeAreaCardProps {
  title: string;
  description: string;
  icon: ReactNode;
  caseCount?: number;
  onPress?: () => void;
  color?: string;
}

export default function PracticeAreaCard({
  title,
  description,
  icon,
  caseCount,
  onPress,
  color = Colors.gold[500],
}: PracticeAreaCardProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.85}
      style={styles.container}
    >
      <View style={[styles.iconContainer, { backgroundColor: color + '20' }]}>
        {icon}
      </View>
      <View style={styles.content}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description} numberOfLines={2}>{description}</Text>
        {caseCount !== undefined && (
          <Text style={styles.count}>{caseCount} active cases</Text>
        )}
      </View>
      <ChevronRight size={16} color={Colors.textMuted} strokeWidth={1.5} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.md,
    ...Shadow.sm,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: BorderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flex: 1,
  },
  title: {
    ...Typography.titleSmall,
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  description: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
  },
  count: {
    ...Typography.labelSmall,
    color: Colors.gold[500],
    marginTop: 4,
  },
});
