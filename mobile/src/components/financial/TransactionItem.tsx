import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ArrowUpRight, ArrowDownLeft, Clock } from 'lucide-react-native';
import { Transaction } from '@store/financialStore';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { formatCurrency, formatDate } from '@utils/formatting';

interface TransactionItemProps {
  transaction: Transaction;
  onPress?: () => void;
}

export default function TransactionItem({ transaction, onPress }: TransactionItemProps) {
  const isCredit = transaction.type === 'credit';
  const amountColor = isCredit ? Colors.success : Colors.textPrimary;
  const Icon = isCredit ? ArrowDownLeft : ArrowUpRight;
  const iconColor = isCredit ? Colors.success : Colors.error;

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.75} style={styles.container}>
      <View style={[styles.iconContainer, { backgroundColor: iconColor + '20' }]}>
        <Icon size={16} color={iconColor} strokeWidth={2} />
      </View>

      <View style={styles.content}>
        <Text style={styles.description} numberOfLines={1}>{transaction.description}</Text>
        <View style={styles.meta}>
          <Text style={styles.category}>{transaction.category}</Text>
          <Text style={styles.separator}>·</Text>
          <Text style={styles.date}>{formatDate(transaction.date, 'MMM d')}</Text>
          {transaction.pending && (
            <>
              <Text style={styles.separator}>·</Text>
              <View style={styles.pendingBadge}>
                <Clock size={9} color={Colors.warning} strokeWidth={2} />
                <Text style={styles.pendingText}>Pending</Text>
              </View>
            </>
          )}
        </View>
      </View>

      <Text style={[styles.amount, { color: amountColor }]}>
        {isCredit ? '+' : '-'}{formatCurrency(Math.abs(transaction.amount))}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    gap: Spacing.md,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: BorderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flex: 1,
  },
  description: {
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    fontWeight: '500',
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    marginTop: 2,
  },
  category: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
    textTransform: 'capitalize',
  },
  separator: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  date: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  pendingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  pendingText: {
    ...Typography.labelSmall,
    color: Colors.warning,
    fontSize: 10,
  },
  amount: {
    ...Typography.titleSmall,
    fontWeight: '600',
  },
});
