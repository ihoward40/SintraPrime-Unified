import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ExternalLink, BookOpen } from 'lucide-react-native';
import { CaseLawResult as CaseLawResultType } from '@api/cases';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { formatDate } from '@utils/formatting';

interface CaseLawResultProps {
  result: CaseLawResultType;
  onPress?: () => void;
}

function RelevanceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct > 80 ? Colors.success : pct > 60 ? Colors.gold[500] : Colors.warning;
  return (
    <View style={relevanceStyles.container}>
      <Text style={[relevanceStyles.label, { color }]}>{pct}% match</Text>
      <View style={relevanceStyles.track}>
        <View style={[relevanceStyles.fill, { width: `${pct}%` as any, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const relevanceStyles = StyleSheet.create({
  container: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  label: { ...Typography.labelSmall, fontWeight: '600', minWidth: 60 },
  track: { flex: 1, height: 4, backgroundColor: Colors.border, borderRadius: 2 },
  fill: { height: 4, borderRadius: 2 },
});

export default function CaseLawResult({ result, onPress }: CaseLawResultProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.85}
      style={styles.container}
    >
      <View style={styles.header}>
        <BookOpen size={14} color={Colors.gold[500]} strokeWidth={1.5} />
        <Text style={styles.citation} numberOfLines={1}>{result.citation}</Text>
        <ExternalLink size={12} color={Colors.textMuted} strokeWidth={1.5} />
      </View>
      <Text style={styles.title} numberOfLines={2}>{result.title}</Text>
      <View style={styles.meta}>
        <Text style={styles.court}>{result.court}</Text>
        <Text style={styles.separator}>·</Text>
        <Text style={styles.date}>{formatDate(result.date, 'yyyy')}</Text>
      </View>
      <Text style={styles.summary} numberOfLines={3}>{result.summary}</Text>
      <RelevanceBar score={result.relevanceScore} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  citation: {
    ...Typography.labelMedium,
    color: Colors.gold[500],
    flex: 1,
  },
  title: {
    ...Typography.titleSmall,
    color: Colors.textPrimary,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  court: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
  },
  separator: {
    color: Colors.textMuted,
  },
  date: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  summary: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
});
