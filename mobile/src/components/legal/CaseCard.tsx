import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Scale, Clock, FileText, ChevronRight } from 'lucide-react-native';
import { LegalCase } from '@store/caseStore';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import { formatDate, formatDeadlineCountdown, getDaysUntil, formatCaseType } from '@utils/formatting';

interface CaseCardProps {
  case_: LegalCase;
  onPress?: () => void;
  compact?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  active: Colors.success,
  pending: Colors.warning,
  closed: Colors.textMuted,
  on_hold: Colors.info,
  won: Colors.success,
  settled: Colors.gold[500],
};

const PRIORITY_COLORS = {
  high: Colors.error,
  medium: Colors.warning,
  low: Colors.success,
};

export default function CaseCard({ case_, onPress, compact = false }: CaseCardProps) {
  const statusColor = STATUS_COLORS[case_.status] ?? Colors.textMuted;
  const daysUntil = case_.deadlineDate ? getDaysUntil(case_.deadlineDate) : null;
  const isUrgent = daysUntil !== null && daysUntil <= 7 && daysUntil >= 0;

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.85}
      style={[styles.container, isUrgent && styles.urgentContainer]}
    >
      {/* Priority indicator */}
      <View style={[styles.priorityBar, { backgroundColor: PRIORITY_COLORS[case_.priority] }]} />

      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.typeTag}>
            <Scale size={10} color={Colors.gold[500]} strokeWidth={2} />
            <Text style={styles.typeText}>{formatCaseType(case_.type)}</Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: statusColor + '20' }]}>
            <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
            <Text style={[styles.statusText, { color: statusColor }]}>
              {case_.status.replace('_', ' ').toUpperCase()}
            </Text>
          </View>
        </View>

        {/* Title */}
        <Text style={styles.title} numberOfLines={compact ? 1 : 2}>
          {case_.title}
        </Text>

        {/* Case number */}
        <Text style={styles.caseNumber}>{case_.caseNumber}</Text>

        {!compact && (
          <>
            {/* Summary */}
            <Text style={styles.summary} numberOfLines={2}>
              {case_.summary}
            </Text>

            {/* Footer */}
            <View style={styles.footer}>
              {case_.deadlineDate && (
                <View style={styles.deadlineRow}>
                  <Clock
                    size={12}
                    color={isUrgent ? Colors.error : Colors.textMuted}
                    strokeWidth={2}
                  />
                  <Text
                    style={[
                      styles.deadlineText,
                      isUrgent && styles.deadlineUrgent,
                    ]}
                  >
                    {formatDeadlineCountdown(case_.deadlineDate)}
                  </Text>
                </View>
              )}
              <View style={styles.docsRow}>
                <FileText size={12} color={Colors.textMuted} strokeWidth={2} />
                <Text style={styles.docsText}>{case_.documentCount} docs</Text>
              </View>
            </View>
          </>
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
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.md,
  },
  urgentContainer: {
    borderColor: Colors.error + '40',
  },
  priorityBar: {
    width: 3,
    alignSelf: 'stretch',
  },
  content: {
    flex: 1,
    padding: Spacing.base,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.sm,
  },
  typeTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  typeText: {
    ...Typography.labelSmall,
    color: Colors.gold[500],
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: 100,
    gap: 4,
  },
  statusDot: {
    width: 5,
    height: 5,
    borderRadius: 100,
  },
  statusText: {
    ...Typography.labelSmall,
    fontSize: 9,
    fontWeight: '700',
  },
  title: {
    ...Typography.titleMedium,
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  caseNumber: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
    marginBottom: Spacing.sm,
    fontFamily: 'monospace',
  },
  summary: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
    lineHeight: 18,
    marginBottom: Spacing.md,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.base,
  },
  deadlineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  deadlineText: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
  },
  deadlineUrgent: {
    color: Colors.error,
    fontWeight: '600',
  },
  docsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  docsText: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
  },
});
