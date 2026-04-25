import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { useFinancialStore } from '@store/financialStore';
import { formatDate, getCreditScoreColor, getCreditScoreLabel, formatPercent } from '@utils/formatting';
import CreditGauge from '@components/financial/CreditGauge';
import GradientHeader from '@components/common/GradientHeader';
import GoldCard from '@components/common/GoldCard';
import { TrendingUp, TrendingDown, Minus, CheckCircle } from 'lucide-react-native';

const IMPROVEMENT_TIPS = [
  'Pay all bills on time — payment history is 35% of your score.',
  'Reduce credit card balances to under 30% of your credit limit.',
  'Avoid applying for new credit in the next 6 months.',
];

export default function CreditScoreScreen() {
  const { creditScore } = useFinancialStore();

  if (!creditScore) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
        <GradientHeader title="Credit Score" showBack />
      </View>
    );
  }

  const change = creditScore.score - creditScore.previousScore;
  const isUp = change > 0;

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader
        title="Credit Score"
        subtitle={`Updated ${formatDate(creditScore.lastUpdated)} · ${creditScore.bureau}`}
        showBack
      />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

          {/* Gauge */}
          <View style={styles.gaugeSection}>
            <CreditGauge score={creditScore.score} size={240} />
            <View style={[styles.changeBadge, { backgroundColor: (isUp ? Colors.success : Colors.error) + '20' }]}>
              {isUp
                ? <TrendingUp size={14} color={Colors.success} strokeWidth={2} />
                : <TrendingDown size={14} color={Colors.error} strokeWidth={2} />
              }
              <Text style={[styles.changeText, { color: isUp ? Colors.success : Colors.error }]}>
                {isUp ? '+' : ''}{change} pts this month
              </Text>
            </View>
          </View>

          {/* Score factors */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Score Factors</Text>
            {creditScore.factors.map((factor) => {
              const pct = factor.score / factor.maxScore;
              const TrendIcon = factor.trend === 'up' ? TrendingUp : factor.trend === 'down' ? TrendingDown : Minus;
              const trendColor = factor.trend === 'up' ? Colors.success : factor.trend === 'down' ? Colors.error : Colors.textMuted;
              return (
                <View key={factor.name} style={styles.factorItem}>
                  <View style={styles.factorHeader}>
                    <Text style={styles.factorName}>{factor.name}</Text>
                    <View style={styles.factorMeta}>
                      <TrendIcon size={12} color={trendColor} strokeWidth={2} />
                      <Text style={[styles.impactBadge, {
                        color: factor.impact === 'high' ? Colors.gold[500] : factor.impact === 'medium' ? Colors.warning : Colors.textMuted
                      }]}>
                        {factor.impact.toUpperCase()} IMPACT
                      </Text>
                    </View>
                  </View>
                  <View style={styles.factorTrack}>
                    <View style={[styles.factorFill, { width: `${pct * 100}%` as any, backgroundColor: getCreditScoreColor(300 + pct * 550) }]} />
                  </View>
                  <Text style={styles.factorPct}>{formatPercent(pct * 100, 0)}</Text>
                </View>
              );
            })}
          </View>

          {/* History */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>6-Month History</Text>
            <GoldCard>
              <View style={styles.historyBar}>
                {creditScore.history.map((h) => {
                  const relativeHeight = ((h.score - 700) / 50) * 60 + 20;
                  return (
                    <View key={h.month} style={styles.historyCol}>
                      <Text style={styles.historyScore}>{h.score}</Text>
                      <View style={[styles.historyBlock, { height: Math.max(relativeHeight, 20), backgroundColor: getCreditScoreColor(h.score) }]} />
                      <Text style={styles.historyMonth}>{h.month}</Text>
                    </View>
                  );
                })}
              </View>
            </GoldCard>
          </View>

          {/* Tips */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🚀 Top Improvement Actions</Text>
            {IMPROVEMENT_TIPS.map((tip, i) => (
              <View key={i} style={styles.tipItem}>
                <CheckCircle size={16} color={Colors.gold[500]} strokeWidth={1.5} />
                <Text style={styles.tipText}>{tip}</Text>
              </View>
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingBottom: Spacing['3xl'] },
  gaugeSection: { alignItems: 'center', paddingVertical: Spacing.xl, gap: Spacing.md },
  changeBadge: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.xs,
    paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
  },
  changeText: { ...Typography.labelMedium, fontWeight: '600' },
  section: { paddingHorizontal: Spacing.base, marginTop: Spacing.xl, gap: Spacing.md },
  sectionTitle: { ...Typography.titleMedium, color: Colors.textPrimary },
  factorItem: { gap: 6 },
  factorHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  factorName: { ...Typography.bodyMedium, color: Colors.textPrimary, fontWeight: '500' },
  factorMeta: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs },
  impactBadge: { ...Typography.labelSmall, fontSize: 9, fontWeight: '700', letterSpacing: 0.5 },
  factorTrack: { height: 8, backgroundColor: Colors.border, borderRadius: BorderRadius.full, overflow: 'hidden' },
  factorFill: { height: '100%', borderRadius: BorderRadius.full },
  factorPct: { ...Typography.labelSmall, color: Colors.textMuted, textAlign: 'right' },
  historyBar: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 100 },
  historyCol: { alignItems: 'center', gap: 4, flex: 1 },
  historyScore: { ...Typography.labelSmall, color: Colors.textMuted, fontSize: 9 },
  historyBlock: { width: 28, borderRadius: 4 },
  historyMonth: { ...Typography.labelSmall, color: Colors.textMuted },
  tipItem: {
    flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.md,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
    borderLeftWidth: 3, borderLeftColor: Colors.gold[500],
  },
  tipText: { ...Typography.bodySmall, color: Colors.textSecondary, flex: 1, lineHeight: 20 },
});
