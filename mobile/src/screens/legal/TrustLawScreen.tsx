import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FileText, Shield, Users, ChevronRight, Bot } from 'lucide-react-native';
import { useNavigation } from '@react-navigation/native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';
import GoldCard from '@components/common/GoldCard';

const TRUST_TOOLS = [
  { id: 'revocable', icon: <Shield size={20} color={Colors.gold[500]} strokeWidth={1.5} />, title: 'Revocable Living Trust', desc: 'Avoid probate and maintain control of assets during your lifetime.' },
  { id: 'irrevocable', icon: <FileText size={20} color={Colors.info} strokeWidth={1.5} />, title: 'Irrevocable Trust', desc: 'Asset protection and tax benefits with transfer of control.' },
  { id: 'testamentary', icon: <FileText size={20} color={Colors.warning} strokeWidth={1.5} />, title: 'Testamentary Trust', desc: 'Created through a will, takes effect upon death.' },
  { id: 'special_needs', icon: <Users size={20} color={Colors.success} strokeWidth={1.5} />, title: 'Special Needs Trust', desc: 'Provide for a beneficiary without affecting government benefits.' },
];

export default function TrustLawScreen() {
  const navigation = useNavigation<any>();

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader title="Trust & Estate Planner" subtitle="AI-guided estate planning" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: Spacing.base, gap: Spacing.md, paddingBottom: Spacing['3xl'] }}>
          <GoldCard>
            <Text style={styles.intro}>
              Create comprehensive trust documents and estate plans with AI guidance. All drafts require attorney review.
            </Text>
          </GoldCard>
          {TRUST_TOOLS.map((tool) => (
            <TouchableOpacity key={tool.id} style={styles.toolCard} activeOpacity={0.85}>
              <View style={styles.toolIcon}>{tool.icon}</View>
              <View style={styles.toolContent}>
                <Text style={styles.toolTitle}>{tool.title}</Text>
                <Text style={styles.toolDesc}>{tool.desc}</Text>
              </View>
              <ChevronRight size={16} color={Colors.textMuted} strokeWidth={1.5} />
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            onPress={() => navigation.navigate('AI', { screen: 'AIAssistant', params: { initialQuery: 'Help me with estate planning and trust creation' } })}
            style={styles.aiBtn}
          >
            <Bot size={18} color={Colors.navy[900]} strokeWidth={1.5} />
            <Text style={styles.aiBtnText}>Ask AI Estate Planner</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  intro: { ...Typography.bodyMedium, color: Colors.textSecondary, lineHeight: 24 },
  toolCard: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl, padding: Spacing.base,
    borderWidth: 1, borderColor: Colors.border,
  },
  toolIcon: { width: 44, height: 44, borderRadius: 12, backgroundColor: Colors.border, alignItems: 'center', justifyContent: 'center' },
  toolContent: { flex: 1 },
  toolTitle: { ...Typography.titleSmall, color: Colors.textPrimary },
  toolDesc: { ...Typography.bodySmall, color: Colors.textSecondary, marginTop: 2 },
  aiBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, backgroundColor: Colors.gold[500],
    borderRadius: BorderRadius.full, paddingVertical: Spacing.base,
    marginTop: Spacing.md,
  },
  aiBtnText: { ...Typography.titleSmall, color: Colors.navy[900], fontWeight: '700' },
});
