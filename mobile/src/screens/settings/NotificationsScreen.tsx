import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, Switch } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Scale, CreditCard, TrendingUp, Bot, FileText, Bell } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';

const NOTIFICATION_SETTINGS = [
  { id: 'case_deadline', label: 'Case Deadlines', desc: '7-day and 1-day warnings', icon: Scale, color: Colors.error },
  { id: 'new_caselaw', label: 'New Case Law', desc: 'Matching your watch terms', icon: Scale, color: Colors.info },
  { id: 'credit_change', label: 'Credit Score Changes', desc: 'Score increases & drops', icon: CreditCard, color: Colors.gold[500] },
  { id: 'large_transaction', label: 'Large Transactions', desc: 'Transactions over $500', icon: TrendingUp, color: Colors.warning },
  { id: 'ai_parliament', label: 'AI Parliament Decisions', desc: 'New recommendations', icon: Bot, color: Colors.success },
  { id: 'document_expiring', label: 'Document Alerts', desc: 'Shared links expiring', icon: FileText, color: Colors.error },
  { id: 'general', label: 'General Updates', desc: 'App news and announcements', icon: Bell, color: Colors.textMuted },
];

export default function NotificationsScreen() {
  const [settings, setSettings] = useState<Record<string, boolean>>(
    Object.fromEntries(NOTIFICATION_SETTINGS.map((s) => [s.id, s.id !== 'general']))
  );

  const toggle = (id: string) => setSettings((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader title="Notification Settings" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.intro}>
            Customize which notifications you receive from SintraPrime.
          </Text>
          <View style={styles.card}>
            {NOTIFICATION_SETTINGS.map((setting, i) => {
              const Icon = setting.icon;
              return (
                <React.Fragment key={setting.id}>
                  <View style={styles.row}>
                    <View style={[styles.icon, { backgroundColor: setting.color + '20' }]}>
                      <Icon size={16} color={setting.color} strokeWidth={1.5} />
                    </View>
                    <View style={styles.rowContent}>
                      <Text style={styles.rowTitle}>{setting.label}</Text>
                      <Text style={styles.rowDesc}>{setting.desc}</Text>
                    </View>
                    <Switch
                      value={settings[setting.id]}
                      onValueChange={() => toggle(setting.id)}
                      trackColor={{ false: Colors.border, true: Colors.gold[500] }}
                      thumbColor={Colors.textPrimary}
                    />
                  </View>
                  {i < NOTIFICATION_SETTINGS.length - 1 && <View style={styles.separator} />}
                </React.Fragment>
              );
            })}
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.base, paddingBottom: Spacing['3xl'] },
  intro: { ...Typography.bodyMedium, color: Colors.textSecondary, lineHeight: 24 },
  card: { backgroundColor: Colors.surface, borderRadius: BorderRadius.xl, borderWidth: 1, borderColor: Colors.border, overflow: 'hidden' },
  row: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.base,
  },
  icon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  rowContent: { flex: 1 },
  rowTitle: { ...Typography.bodyMedium, color: Colors.textPrimary },
  rowDesc: { ...Typography.bodySmall, color: Colors.textMuted },
  separator: { height: 1, backgroundColor: Colors.border, marginLeft: 16 + 36 + 16 },
});
