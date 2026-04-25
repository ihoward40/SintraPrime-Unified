import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { TrendingUp, Banknote, Users, Star, ChevronRight } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';

const MOCK_FUNDING = [
  {
    id: 'f1',
    name: 'SBA 7(a) Small Business Loan',
    provider: 'U.S. Small Business Administration',
    type: 'sba',
    amount: { min: 50000, max: 5000000 },
    interestRate: 6.5,
    requirements: ['2+ years in business', '680+ credit score', '$50K+ annual revenue'],
    matchScore: 0.94,
    description: 'Flexible government-backed loan for a wide range of business purposes.',
  },
  {
    id: 'f2',
    name: 'Minority Business Development Grant',
    provider: 'MBDA',
    type: 'grant',
    amount: { min: 25000, max: 250000 },
    requirements: ['Minority-owned business', 'U.S. citizen', 'Active business plan'],
    matchScore: 0.87,
    description: 'Federal grant for minority-owned businesses to scale operations.',
  },
  {
    id: 'f3',
    name: 'Series A Venture Capital',
    provider: 'SintraPrime Ventures Network',
    type: 'investor',
    amount: { min: 500000, max: 5000000 },
    requirements: ['Scalable business model', 'Proven revenue', 'Strong team'],
    matchScore: 0.76,
    description: 'Connect with our network of 200+ accredited investors.',
  },
];

const TYPE_ICONS: Record<string, any> = {
  sba: Banknote,
  grant: Star,
  investor: Users,
  loan: Banknote,
  crowdfunding: TrendingUp,
};

const TYPE_COLORS: Record<string, string> = {
  sba: Colors.info,
  grant: Colors.success,
  investor: Colors.gold[500],
  loan: Colors.warning,
  crowdfunding: Colors.error,
};

export default function FundingScreen() {
  const [filter, setFilter] = useState<string>('all');
  const FILTERS = ['all', 'sba', 'grant', 'investor', 'loan'];

  const filtered = filter === 'all' ? MOCK_FUNDING : MOCK_FUNDING.filter((f) => f.type === filter);

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader title="Find Funding" subtitle="AI-matched opportunities" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Filters */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
            {FILTERS.map((f) => (
              <TouchableOpacity
                key={f}
                onPress={() => setFilter(f)}
                style={[styles.filterChip, filter === f && styles.filterChipActive]}
              >
                <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Cards */}
          {filtered.map((item) => {
            const Icon = TYPE_ICONS[item.type] ?? Banknote;
            const color = TYPE_COLORS[item.type] ?? Colors.gold[500];
            const matchPct = Math.round(item.matchScore * 100);
            return (
              <TouchableOpacity key={item.id} style={styles.card} activeOpacity={0.85}>
                <View style={styles.cardHeader}>
                  <View style={[styles.cardIcon, { backgroundColor: color + '20' }]}>
                    <Icon size={18} color={color} strokeWidth={1.5} />
                  </View>
                  <View style={styles.cardMeta}>
                    <Text style={styles.cardType}>{item.type.toUpperCase()}</Text>
                    <View style={[styles.matchBadge, { backgroundColor: matchPct > 85 ? Colors.success + '20' : Colors.warning + '20' }]}>
                      <Text style={[styles.matchText, { color: matchPct > 85 ? Colors.success : Colors.warning }]}>
                        {matchPct}% match
                      </Text>
                    </View>
                  </View>
                </View>
                <Text style={styles.cardName}>{item.name}</Text>
                <Text style={styles.cardProvider}>{item.provider}</Text>
                <Text style={styles.cardDesc} numberOfLines={2}>{item.description}</Text>
                <View style={styles.amountRow}>
                  <Text style={styles.amountLabel}>Funding Range:</Text>
                  <Text style={styles.amountValue}>
                    ${(item.amount.min / 1000).toFixed(0)}K – ${(item.amount.max / 1000000).toFixed(1)}M
                  </Text>
                </View>
                <View style={styles.requirementsRow}>
                  {item.requirements.slice(0, 2).map((req, i) => (
                    <View key={i} style={styles.reqChip}>
                      <Text style={styles.reqText}>{req}</Text>
                    </View>
                  ))}
                </View>
                <TouchableOpacity style={styles.applyBtn}>
                  <Text style={styles.applyText}>Learn More & Apply</Text>
                  <ChevronRight size={14} color={Colors.navy[900]} strokeWidth={2} />
                </TouchableOpacity>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.md, paddingBottom: Spacing['3xl'] },
  filters: { gap: Spacing.sm, marginBottom: Spacing.sm },
  filterChip: {
    paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
  },
  filterChipActive: { backgroundColor: Colors.gold[500] + '20', borderColor: Colors.gold[500] },
  filterText: { ...Typography.labelSmall, color: Colors.textMuted },
  filterTextActive: { color: Colors.gold[500], fontWeight: '600' },
  card: {
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border, gap: Spacing.sm,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  cardIcon: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  cardMeta: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cardType: { ...Typography.labelSmall, color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  matchBadge: { paddingHorizontal: Spacing.sm, paddingVertical: 2, borderRadius: BorderRadius.full },
  matchText: { ...Typography.labelSmall, fontWeight: '600' },
  cardName: { ...Typography.titleSmall, color: Colors.textPrimary },
  cardProvider: { ...Typography.bodySmall, color: Colors.textMuted },
  cardDesc: { ...Typography.bodySmall, color: Colors.textSecondary, lineHeight: 18 },
  amountRow: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'center' },
  amountLabel: { ...Typography.bodySmall, color: Colors.textMuted },
  amountValue: { ...Typography.bodySmall, color: Colors.gold[400], fontWeight: '600' },
  requirementsRow: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap' },
  reqChip: {
    paddingHorizontal: Spacing.sm, paddingVertical: 3,
    backgroundColor: Colors.border, borderRadius: BorderRadius.full,
  },
  reqText: { ...Typography.labelSmall, color: Colors.textSecondary, fontSize: 10 },
  applyBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.xs, backgroundColor: Colors.gold[500],
    borderRadius: BorderRadius.full, paddingVertical: Spacing.sm,
    marginTop: Spacing.xs,
  },
  applyText: { ...Typography.labelLarge, color: Colors.navy[900], fontWeight: '700' },
});
