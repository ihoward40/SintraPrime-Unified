import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import {
  CreditCard,
  PieChart,
  TrendingUp,
  Banknote,
  ChevronRight,
  Plus,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import { useFinancialStore } from '@store/financialStore';
import {
  formatCurrencyCompact,
  formatCurrency,
  formatPercent,
  getCreditScoreColor,
  getCreditScoreLabel,
} from '@utils/formatting';
import AccountCard from '@components/financial/AccountCard';
import GradientHeader from '@components/common/GradientHeader';
import StatBadge from '@components/common/StatBadge';

const MENU_ITEMS = [
  { id: 'accounts', label: 'Linked Accounts', icon: Banknote, color: Colors.info, screen: 'Accounts' },
  { id: 'credit', label: 'Credit Score', icon: CreditCard, color: Colors.success, screen: 'CreditScore' },
  { id: 'budget', label: 'Budget Tracker', icon: PieChart, color: Colors.warning, screen: 'Budget' },
  { id: 'funding', label: 'Find Funding', icon: TrendingUp, color: Colors.gold[500], screen: 'Funding' },
];

export default function FinancialScreen() {
  const navigation = useNavigation<any>();
  const { accounts, creditScore, netWorth, monthlyIncome, monthlyExpenses } = useFinancialStore();
  const surplus = monthlyIncome - monthlyExpenses;

  return (
    <View style={styles.container}>
      <GradientHeader
        title="Financial Dashboard"
        subtitle="Your complete financial picture"
        rightAction={
          <TouchableOpacity style={styles.addBtn}>
            <Plus size={18} color={Colors.navy[900]} strokeWidth={2} />
          </TouchableOpacity>
        }
      />

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {/* Net worth hero */}
          <LinearGradient
            colors={[Colors.navy[800], Colors.navy[900]]}
            style={styles.netWorthCard}
          >
            <Text style={styles.netWorthLabel}>Total Net Worth</Text>
            <Text style={styles.netWorthValue}>{formatCurrencyCompact(netWorth)}</Text>
            <View style={styles.netWorthStats}>
              <StatBadge
                label="Income"
                value={formatCurrencyCompact(monthlyIncome)}
                trend="stable"
              />
              <View style={styles.statDivider} />
              <StatBadge
                label="Expenses"
                value={formatCurrencyCompact(monthlyExpenses)}
              />
              <View style={styles.statDivider} />
              <StatBadge
                label="Surplus"
                value={formatCurrencyCompact(surplus)}
                trend={surplus > 0 ? 'up' : 'down'}
                accent={surplus > 0}
              />
            </View>
          </LinearGradient>

          {/* Accounts horizontal scroll */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Accounts</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Accounts')} style={styles.seeAll}>
                <Text style={styles.seeAllText}>All accounts</Text>
                <ChevronRight size={14} color={Colors.gold[500]} strokeWidth={2} />
              </TouchableOpacity>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.accountsScroll}
            >
              {accounts.map((acc) => (
                <AccountCard
                  key={acc.id}
                  account={acc}
                  onPress={() => navigation.navigate('Accounts')}
                />
              ))}
            </ScrollView>
          </View>

          {/* Credit score teaser */}
          {creditScore && (
            <TouchableOpacity
              onPress={() => navigation.navigate('CreditScore')}
              style={styles.creditCard}
              activeOpacity={0.85}
            >
              <View>
                <Text style={styles.creditCardLabel}>Credit Score</Text>
                <Text style={[styles.creditCardScore, { color: getCreditScoreColor(creditScore.score) }]}>
                  {creditScore.score}
                </Text>
                <Text style={styles.creditCardRating}>{getCreditScoreLabel(creditScore.score)}</Text>
              </View>
              <View style={styles.creditCardRight}>
                <Text style={styles.creditCardChange}>
                  +{creditScore.score - creditScore.previousScore} pts
                </Text>
                <Text style={styles.creditCardChangeSub}>this month</Text>
                <ChevronRight size={18} color={Colors.textMuted} strokeWidth={1.5} style={{ marginTop: Spacing.sm }} />
              </View>
            </TouchableOpacity>
          )}

          {/* Menu items */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Tools & Insights</Text>
            {MENU_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <TouchableOpacity
                  key={item.id}
                  onPress={() => navigation.navigate(item.screen)}
                  activeOpacity={0.85}
                  style={styles.menuItem}
                >
                  <View style={[styles.menuIcon, { backgroundColor: item.color + '20' }]}>
                    <Icon size={18} color={item.color} strokeWidth={1.5} />
                  </View>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                  <ChevronRight size={16} color={Colors.textMuted} strokeWidth={1.5} />
                </TouchableOpacity>
              );
            })}
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  addBtn: {
    width: 36, height: 36, borderRadius: 12,
    backgroundColor: Colors.gold[500],
    alignItems: 'center', justifyContent: 'center',
  },
  scroll: { paddingBottom: Spacing['3xl'] },
  netWorthCard: {
    margin: Spacing.base,
    borderRadius: BorderRadius['2xl'],
    padding: Spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.gold,
    borderBottomColor: Colors.gold[500] + '40',
  },
  netWorthLabel: { ...Typography.labelMedium, color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 1 },
  netWorthValue: { fontSize: 48, fontWeight: '800', color: Colors.gold[400], letterSpacing: -2, marginVertical: Spacing.sm },
  netWorthStats: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xl, marginTop: Spacing.md },
  statDivider: { width: 1, height: 36, backgroundColor: Colors.border },
  section: { paddingHorizontal: Spacing.base, marginTop: Spacing.xl, gap: Spacing.md },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sectionTitle: { ...Typography.titleMedium, color: Colors.textPrimary },
  seeAll: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  seeAllText: { ...Typography.labelMedium, color: Colors.gold[500] },
  accountsScroll: { gap: Spacing.md, paddingRight: Spacing.base },
  creditCard: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginHorizontal: Spacing.base, marginTop: Spacing.xl,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl, padding: Spacing.base,
    borderWidth: 1, borderColor: Colors.border,
    ...Shadow.md,
  },
  creditCardLabel: { ...Typography.labelSmall, color: Colors.textMuted, textTransform: 'uppercase' },
  creditCardScore: { fontSize: 40, fontWeight: '800', letterSpacing: -1 },
  creditCardRating: { ...Typography.bodySmall, color: Colors.textSecondary },
  creditCardRight: { alignItems: 'flex-end' },
  creditCardChange: { ...Typography.titleMedium, color: Colors.success, fontWeight: '700' },
  creditCardChangeSub: { ...Typography.bodySmall, color: Colors.textMuted },
  menuItem: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
  },
  menuIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  menuLabel: { ...Typography.titleSmall, color: Colors.textPrimary, flex: 1 },
});
