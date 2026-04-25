import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Plus, Link } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { useFinancialStore } from '@store/financialStore';
import { formatCurrency } from '@utils/formatting';
import AccountCard from '@components/financial/AccountCard';
import GradientHeader from '@components/common/GradientHeader';

export default function AccountsScreen() {
  const { accounts, getTotalBalance } = useFinancialStore();

  const grouped = accounts.reduce<Record<string, typeof accounts>>((acc, a) => {
    const key = a.institution;
    if (!acc[key]) acc[key] = [];
    acc[key].push(a);
    return acc;
  }, {});

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader
        title="Linked Accounts"
        subtitle={`${accounts.length} accounts`}
        showBack
        rightAction={
          <TouchableOpacity style={styles.addBtn}>
            <Plus size={18} color={Colors.navy[900]} strokeWidth={2} />
          </TouchableOpacity>
        }
      />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.totalCard}>
            <Text style={styles.totalLabel}>Total Balance</Text>
            <Text style={styles.totalValue}>{formatCurrency(getTotalBalance())}</Text>
          </View>

          {Object.entries(grouped).map(([institution, accs]) => (
            <View key={institution} style={styles.group}>
              <Text style={styles.groupLabel}>{institution}</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: Spacing.md }}>
                {accs.map((acc) => (
                  <AccountCard key={acc.id} account={acc} />
                ))}
              </ScrollView>
            </View>
          ))}

          <TouchableOpacity style={styles.linkBtn}>
            <Link size={18} color={Colors.gold[500]} strokeWidth={1.5} />
            <Text style={styles.linkText}>Link a New Account</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.xl, paddingBottom: Spacing['3xl'] },
  addBtn: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: Colors.gold[500],
    alignItems: 'center', justifyContent: 'center',
  },
  totalCard: {
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.xl, alignItems: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  totalLabel: {
    ...Typography.labelMedium, color: Colors.textMuted,
    textTransform: 'uppercase', letterSpacing: 1,
  },
  totalValue: {
    fontSize: 36, fontWeight: '800',
    color: Colors.gold[400], letterSpacing: -1, marginTop: Spacing.xs,
  },
  group: { gap: Spacing.md },
  groupLabel: { ...Typography.titleSmall, color: Colors.textSecondary },
  linkBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, borderWidth: 1.5, borderColor: Colors.gold[500],
    borderRadius: BorderRadius.full, paddingVertical: Spacing.base,
  },
  linkText: { ...Typography.labelLarge, color: Colors.gold[500] },
});
