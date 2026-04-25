import React, { useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  FlatList,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import {
  Bot,
  Scale,
  CreditCard,
  Wallet,
  Bell,
  ChevronRight,
  AlertCircle,
  TrendingUp,
} from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import { useAuthStore } from '@store/authStore';
import { useCaseStore } from '@store/caseStore';
import { useFinancialStore } from '@store/financialStore';
import {
  getGreeting,
  formatCurrencyCompact,
  formatDeadlineCountdown,
  getDaysUntil,
  getCreditScoreColor,
  getCreditScoreLabel,
} from '@utils/formatting';
import CaseCard from '@components/legal/CaseCard';
import StatBadge from '@components/common/StatBadge';
import GoldCard from '@components/common/GoldCard';

const QUICK_ACTIONS = [
  { id: 'ai', label: 'Ask AI', icon: Bot, color: Colors.gold[500], screen: 'AI' },
  { id: 'case', label: 'New Case', icon: Scale, color: Colors.info, screen: 'Legal' },
  { id: 'credit', label: 'Credit', icon: CreditCard, color: Colors.success, screen: 'Financial' },
  { id: 'funding', label: 'Funding', icon: Wallet, color: Colors.warning, screen: 'Financial' },
];

export default function HomeScreen() {
  const navigation = useNavigation<any>();
  const { user } = useAuthStore();
  const { cases, getActiveCases } = useCaseStore();
  const { creditScore, netWorth, monthlyIncome, monthlyExpenses } = useFinancialStore();

  const [refreshing, setRefreshing] = React.useState(false);
  const activeCases = getActiveCases();

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    // Trigger data refresh
    await new Promise((r) => setTimeout(r, 1200));
    setRefreshing(false);
  }, []);

  // Upcoming deadlines
  const deadlines = cases
    .filter((c) => c.deadlineDate && getDaysUntil(c.deadlineDate) <= 14 && getDaysUntil(c.deadlineDate) >= 0)
    .sort((a, b) => getDaysUntil(a.deadlineDate!) - getDaysUntil(b.deadlineDate!))
    .slice(0, 3);

  const aiInsights = [
    'Your credit utilization dropped 8% — keep it under 30% for best score impact.',
    'Johnson v. Meridian: Consider filing a motion for summary judgment by May 2.',
    'New precedent: Martinez v. Corp Holdings (2026) — relevant to your employment case.',
  ];

  return (
    <View style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.gold[500]}
            colors={[Colors.gold[500]]}
          />
        }
        contentContainerStyle={styles.scroll}
      >
        {/* Header */}
        <LinearGradient
          colors={[Colors.navy[950], Colors.navy[900]]}
          style={styles.header}
        >
          <SafeAreaView edges={['top']}>
            <View style={styles.headerContent}>
              <View>
                <Text style={styles.greeting}>
                  {getGreeting()}, {user?.firstName ?? 'Counselor'} 👋
                </Text>
                <Text style={styles.headerSub}>
                  {activeCases.length} active {activeCases.length === 1 ? 'case' : 'cases'}
                </Text>
              </View>
              <TouchableOpacity style={styles.bellBtn}>
                <Bell size={22} color={Colors.textSecondary} strokeWidth={1.5} />
                <View style={styles.bellDot} />
              </TouchableOpacity>
            </View>
          </SafeAreaView>

          {/* Financial snapshot */}
          <View style={styles.snapshotRow}>
            <StatBadge
              label="Net Worth"
              value={formatCurrencyCompact(netWorth)}
              trend="up"
              trendValue="+2.4%"
              accent
              size="lg"
            />
            <View style={styles.snapshotDivider} />
            <StatBadge
              label="Monthly Surplus"
              value={formatCurrencyCompact(monthlyIncome - monthlyExpenses)}
              trend="up"
              trendValue="+$340"
            />
            <View style={styles.snapshotDivider} />
            {creditScore && (
              <StatBadge
                label="Credit Score"
                value={creditScore.score}
                trend="up"
                trendValue={`+${creditScore.score - creditScore.previousScore}`}
              />
            )}
          </View>

          {/* Gold accent */}
          <View style={styles.headerAccent} />
        </LinearGradient>

        {/* Quick Actions */}
        <View style={styles.section}>
          <View style={styles.quickGrid}>
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <TouchableOpacity
                  key={action.id}
                  onPress={() => navigation.navigate(action.screen)}
                  activeOpacity={0.8}
                  style={styles.quickAction}
                >
                  <View style={[styles.quickIcon, { backgroundColor: action.color + '20' }]}>
                    <Icon size={22} color={action.color} strokeWidth={1.5} />
                  </View>
                  <Text style={styles.quickLabel}>{action.label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* Active Cases */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Active Cases</Text>
            <TouchableOpacity
              onPress={() => navigation.navigate('Legal')}
              style={styles.seeAll}
            >
              <Text style={styles.seeAllText}>See all</Text>
              <ChevronRight size={14} color={Colors.gold[500]} strokeWidth={2} />
            </TouchableOpacity>
          </View>

          {activeCases.length === 0 ? (
            <GoldCard>
              <Text style={styles.emptyText}>No active cases. Start a new case to get legal AI support.</Text>
            </GoldCard>
          ) : (
            <FlatList
              data={activeCases.slice(0, 3)}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <CaseCard
                  case_={item}
                  onPress={() =>
                    navigation.navigate('Legal', {
                      screen: 'CaseDetail',
                      params: { caseId: item.id, caseTitle: item.title },
                    })
                  }
                  style={styles.caseCard}
                />
              )}
              scrollEnabled={false}
              ItemSeparatorComponent={() => <View style={{ height: Spacing.sm }} />}
            />
          )}
        </View>

        {/* Credit Score */}
        {creditScore && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Credit Score</Text>
              <TouchableOpacity
                onPress={() => navigation.navigate('Financial', { screen: 'CreditScore' })}
                style={styles.seeAll}
              >
                <Text style={styles.seeAllText}>Details</Text>
                <ChevronRight size={14} color={Colors.gold[500]} strokeWidth={2} />
              </TouchableOpacity>
            </View>
            <GoldCard onPress={() => navigation.navigate('Financial', { screen: 'CreditScore' })}>
              <View style={styles.creditRow}>
                <View>
                  <Text
                    style={[
                      styles.creditScore,
                      { color: getCreditScoreColor(creditScore.score) },
                    ]}
                  >
                    {creditScore.score}
                  </Text>
                  <Text style={styles.creditLabel}>
                    {getCreditScoreLabel(creditScore.score)}
                  </Text>
                </View>
                <View style={styles.creditChange}>
                  <TrendingUp size={16} color={Colors.success} strokeWidth={2} />
                  <Text style={styles.creditChangeText}>
                    +{creditScore.score - creditScore.previousScore} pts this month
                  </Text>
                </View>
              </View>
            </GoldCard>
          </View>
        )}

        {/* Upcoming Deadlines */}
        {deadlines.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>⚠️ Upcoming Deadlines</Text>
            </View>
            {deadlines.map((c) => (
              <TouchableOpacity
                key={c.id}
                style={styles.deadlineItem}
                onPress={() =>
                  navigation.navigate('Legal', {
                    screen: 'CaseDetail',
                    params: { caseId: c.id, caseTitle: c.title },
                  })
                }
              >
                <AlertCircle
                  size={16}
                  color={getDaysUntil(c.deadlineDate!) <= 3 ? Colors.error : Colors.warning}
                  strokeWidth={2}
                />
                <View style={styles.deadlineContent}>
                  <Text style={styles.deadlineTitle} numberOfLines={1}>{c.title}</Text>
                  <Text style={styles.deadlineCountdown}>
                    {formatDeadlineCountdown(c.deadlineDate!)}
                  </Text>
                </View>
                <ChevronRight size={14} color={Colors.textMuted} strokeWidth={1.5} />
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* AI Insights */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>🤖 AI Insights Today</Text>
            <TouchableOpacity
              onPress={() => navigation.navigate('AI')}
              style={styles.seeAll}
            >
              <Text style={styles.seeAllText}>Ask AI</Text>
              <ChevronRight size={14} color={Colors.gold[500]} strokeWidth={2} />
            </TouchableOpacity>
          </View>
          {aiInsights.map((insight, i) => (
            <View key={i} style={styles.insightItem}>
              <View style={styles.insightDot} />
              <Text style={styles.insightText}>{insight}</Text>
            </View>
          ))}
        </View>

        <View style={{ height: Spacing['3xl'] }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scroll: {
    flexGrow: 1,
  },
  header: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.xl,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: Spacing.md,
    paddingBottom: Spacing.lg,
  },
  greeting: {
    ...Typography.headlineSmall,
    color: Colors.textPrimary,
  },
  headerSub: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  bellBtn: {
    position: 'relative',
    padding: Spacing.sm,
  },
  bellDot: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.error,
    borderWidth: 1.5,
    borderColor: Colors.navy[900],
  },
  snapshotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.md,
  },
  snapshotDivider: {
    width: 1,
    height: 40,
    backgroundColor: Colors.border,
    marginHorizontal: Spacing.base,
  },
  headerAccent: {
    height: 2,
    backgroundColor: Colors.gold[500],
    borderRadius: 1,
    marginTop: Spacing.base,
    opacity: 0.4,
  },
  section: {
    paddingHorizontal: Spacing.base,
    marginTop: Spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    ...Typography.titleMedium,
    color: Colors.textPrimary,
  },
  seeAll: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  seeAllText: {
    ...Typography.labelMedium,
    color: Colors.gold[500],
  },
  quickGrid: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  quickAction: {
    flex: 1,
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  quickIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickLabel: {
    ...Typography.labelSmall,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  caseCard: {
    marginBottom: 0,
  },
  emptyText: {
    ...Typography.bodyMedium,
    color: Colors.textSecondary,
    textAlign: 'center',
    padding: Spacing.md,
  },
  creditRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  creditScore: {
    fontSize: 40,
    fontWeight: '800',
    letterSpacing: -1,
  },
  creditLabel: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
  },
  creditChange: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: Colors.success + '20',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
  },
  creditChangeText: {
    ...Typography.labelSmall,
    color: Colors.success,
    fontWeight: '600',
  },
  deadlineItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  deadlineContent: {
    flex: 1,
  },
  deadlineTitle: {
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    fontWeight: '500',
  },
  deadlineCountdown: {
    ...Typography.labelSmall,
    color: Colors.warning,
    marginTop: 2,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    borderLeftWidth: 3,
    borderLeftColor: Colors.gold[500],
  },
  insightDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.gold[500],
    marginTop: 7,
    flexShrink: 0,
  },
  insightText: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
    flex: 1,
    lineHeight: 20,
  },
});
