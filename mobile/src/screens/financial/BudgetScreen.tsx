import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing } from '@theme/spacing';
import { useFinancialStore } from '@store/financialStore';
import { formatCurrency } from '@utils/formatting';
import BudgetBar from '@components/financial/BudgetBar';
import GradientHeader from '@components/common/GradientHeader';
import GoldCard from '@components/common/GoldCard';
import StatBadge from '@components/common/StatBadge';

export default function BudgetScreen() {
  const { budgetCategories, monthlyIncome, monthlyExpenses } = useFinancialStore();
  const totalBudgeted = budgetCategories.reduce((s, c) => s + c.budgeted, 0);
  const totalSpent = budgetCategories.reduce((s, c) => s + c.spent, 0);
  const surplus = totalBudgeted - totalSpent;

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader title="Budget Tracker" subtitle="Monthly spending overview" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <GoldCard style={styles.summaryCard}>
            <View style={styles.summaryRow}>
              <StatBadge label="Budgeted" value={formatCurrency(totalBudgeted, 'USD', { maximumFractionDigits: 0 })} />
              <View style={styles.divider} />
              <StatBadge label="Spent" value={formatCurrency(totalSpent, 'USD', { maximumFractionDigits: 0 })} />
              <View style={styles.divider} />
              <StatBadge
                label={surplus >= 0 ? 'Remaining' : 'Over'}
                value={formatCurrency(Math.abs(surplus), 'USD', { maximumFractionDigits: 0 })}
                accent={surplus >= 0}
              />
            </View>
          </GoldCard>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Categories</Text>
            {budgetCategories.map((cat) => (
              <BudgetBar key={cat.id} category={cat} />
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.xl, paddingBottom: Spacing['3xl'] },
  summaryCard: { padding: Spacing.base },
  summaryRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  divider: { width: 1, height: 36, backgroundColor: Colors.border },
  section: { gap: Spacing.base },
  sectionTitle: { ...Typography.titleMedium, color: Colors.textPrimary },
});
