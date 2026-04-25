import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Building2, TrendingUp, CreditCard, PiggyBank, Bitcoin } from 'lucide-react-native';
import { Account } from '@store/financialStore';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import { formatCurrency } from '@utils/formatting';

const ACCOUNT_TYPE_CONFIG = {
  checking: { icon: Building2, gradient: [Colors.navy[700], Colors.navy[800]], label: 'Checking' },
  savings: { icon: PiggyBank, gradient: [Colors.info + 'CC', Colors.navy[800]], label: 'Savings' },
  investment: { icon: TrendingUp, gradient: [Colors.gold[600], Colors.gold[800]], label: 'Investment' },
  credit: { icon: CreditCard, gradient: [Colors.navy[600], Colors.navy[900]], label: 'Credit Card' },
  loan: { icon: Building2, gradient: [Colors.error + 'AA', Colors.navy[900]], label: 'Loan' },
  crypto: { icon: Bitcoin, gradient: [Colors.warning + 'CC', Colors.navy[800]], label: 'Crypto' },
};

interface AccountCardProps {
  account: Account;
  onPress?: () => void;
  size?: 'sm' | 'md';
}

export default function AccountCard({ account, onPress, size = 'md' }: AccountCardProps) {
  const config = ACCOUNT_TYPE_CONFIG[account.type] ?? ACCOUNT_TYPE_CONFIG.checking;
  const IconComp = config.icon;
  const isNegative = account.balance < 0;

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.85}>
      <LinearGradient
        colors={config.gradient as string[]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.container, size === 'sm' && styles.containerSm, Shadow.lg]}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.iconWrap}>
            <IconComp size={16} color={Colors.gold[300]} strokeWidth={1.5} />
          </View>
          <Text style={styles.typeLabel}>{config.label}</Text>
          {account.lastFour && (
            <Text style={styles.lastFour}>•••• {account.lastFour}</Text>
          )}
        </View>

        {/* Balance */}
        <Text style={[styles.balance, isNegative && styles.balanceNegative]}>
          {formatCurrency(Math.abs(account.balance))}
          {isNegative && <Text style={styles.oweLabel}> owed</Text>}
        </Text>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.institution}>{account.institution}</Text>
          {account.name && (
            <Text style={styles.name} numberOfLines={1}>{account.name}</Text>
          )}
        </View>

        {/* Gold accent */}
        <View style={styles.goldAccent} />
      </LinearGradient>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    width: 200,
    height: 130,
    borderRadius: BorderRadius['2xl'],
    padding: Spacing.base,
    justifyContent: 'space-between',
    overflow: 'hidden',
  },
  containerSm: {
    width: 170,
    height: 110,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  iconWrap: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  typeLabel: {
    ...Typography.labelSmall,
    color: Colors.gold[200],
    flex: 1,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  lastFour: {
    ...Typography.labelSmall,
    color: 'rgba(255,255,255,0.6)',
    fontFamily: 'monospace',
  },
  balance: {
    ...Typography.headlineSmall,
    color: Colors.textPrimary,
    fontWeight: '700',
  },
  balanceNegative: {
    color: Colors.errorLight,
  },
  oweLabel: {
    ...Typography.bodySmall,
    color: Colors.errorLight,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  institution: {
    ...Typography.labelSmall,
    color: 'rgba(255,255,255,0.7)',
    fontWeight: '600',
  },
  name: {
    ...Typography.labelSmall,
    color: 'rgba(255,255,255,0.5)',
    flex: 1,
    textAlign: 'right',
    marginLeft: Spacing.xs,
  },
  goldAccent: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: Colors.gold[400],
    opacity: 0.6,
  },
});
