import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Users, Scale, TrendingUp, Shield, Gavel, Bot } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';

const AI_AGENTS = [
  { id: 'legal', name: 'Lex', role: 'Lead Legal Counsel', specialty: 'Civil & Employment Law', icon: Scale, color: Colors.gold[500], status: 'active' },
  { id: 'tax', name: 'Vera', role: 'Tax Strategist', specialty: 'Tax Law & IRS Representation', icon: TrendingUp, color: Colors.success, status: 'active' },
  { id: 'estate', name: 'Marcus', role: 'Estate Planner', specialty: 'Trusts, Wills & Probate', icon: Shield, color: Colors.info, status: 'active' },
  { id: 'litigation', name: 'Phoenix', role: 'Litigation Specialist', specialty: 'Trial Strategy & Motions', icon: Gavel, color: Colors.error, status: 'active' },
  { id: 'financial', name: 'Nova', role: 'Financial Advisor', specialty: 'Investment & Credit Strategy', icon: TrendingUp, color: Colors.warning, status: 'active' },
];

const RECENT_DECISIONS = [
  { id: 'd1', topic: 'Johnson Case Strategy', agents: ['Lex', 'Phoenix'], decision: 'Recommend filing for summary judgment', date: 'Apr 23, 2026', outcome: 'approved' },
  { id: 'd2', topic: 'Trust Structure for Williams Estate', agents: ['Marcus', 'Vera'], decision: 'Establish irrevocable dynasty trust', date: 'Apr 20, 2026', outcome: 'approved' },
];

export default function ParliamentScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader
        title="AI Parliament"
        subtitle="Your council of specialized AI agents"
        showBack
      />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.intro}>
            The SintraPrime AI Parliament is a council of specialized AI agents that collaborate to provide comprehensive legal and financial guidance.
          </Text>

          {/* Agents */}
          <Text style={styles.sectionTitle}>Your AI Council</Text>
          {AI_AGENTS.map((agent) => {
            const Icon = agent.icon;
            return (
              <View key={agent.id} style={styles.agentCard}>
                <View style={[styles.agentIcon, { backgroundColor: agent.color + '20' }]}>
                  <Icon size={22} color={agent.color} strokeWidth={1.5} />
                </View>
                <View style={styles.agentInfo}>
                  <View style={styles.agentHeader}>
                    <Text style={styles.agentName}>{agent.name}</Text>
                    <View style={styles.activeBadge}>
                      <View style={styles.activeDot} />
                      <Text style={styles.activeText}>Active</Text>
                    </View>
                  </View>
                  <Text style={styles.agentRole}>{agent.role}</Text>
                  <Text style={styles.agentSpecialty}>{agent.specialty}</Text>
                </View>
              </View>
            );
          })}

          {/* Recent decisions */}
          <Text style={[styles.sectionTitle, { marginTop: Spacing.lg }]}>Recent Parliament Decisions</Text>
          {RECENT_DECISIONS.map((decision) => (
            <View key={decision.id} style={styles.decisionCard}>
              <View style={styles.decisionHeader}>
                <Text style={styles.decisionTopic}>{decision.topic}</Text>
                <View style={[styles.outcomeBadge, { backgroundColor: Colors.success + '20' }]}>
                  <Text style={[styles.outcomeText, { color: Colors.success }]}>{decision.outcome}</Text>
                </View>
              </View>
              <Text style={styles.decisionText}>{decision.decision}</Text>
              <View style={styles.decisionMeta}>
                <Text style={styles.decisionAgents}>By: {decision.agents.join(' + ')}</Text>
                <Text style={styles.decisionDate}>{decision.date}</Text>
              </View>
            </View>
          ))}

          {/* Convene button */}
          <TouchableOpacity style={styles.conveneBtn}>
            <Users size={18} color={Colors.navy[900]} strokeWidth={1.5} />
            <Text style={styles.conveneText}>Convene Full Parliament Session</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.md, paddingBottom: Spacing['3xl'] },
  intro: { ...Typography.bodyMedium, color: Colors.textSecondary, lineHeight: 24 },
  sectionTitle: { ...Typography.titleMedium, color: Colors.textPrimary },
  agentCard: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
  },
  agentIcon: { width: 52, height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  agentInfo: { flex: 1 },
  agentHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  agentName: { ...Typography.titleSmall, color: Colors.textPrimary },
  activeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.success + '20', paddingHorizontal: Spacing.sm, paddingVertical: 2, borderRadius: BorderRadius.full },
  activeDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.success },
  activeText: { ...Typography.labelSmall, color: Colors.success, fontWeight: '600' },
  agentRole: { ...Typography.bodySmall, color: Colors.gold[500], marginTop: 2 },
  agentSpecialty: { ...Typography.bodySmall, color: Colors.textMuted, marginTop: 1 },
  decisionCard: {
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border, gap: Spacing.sm,
  },
  decisionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  decisionTopic: { ...Typography.titleSmall, color: Colors.textPrimary, flex: 1 },
  outcomeBadge: { paddingHorizontal: Spacing.sm, paddingVertical: 2, borderRadius: BorderRadius.full, marginLeft: Spacing.sm },
  outcomeText: { ...Typography.labelSmall, fontWeight: '600', textTransform: 'capitalize' },
  decisionText: { ...Typography.bodySmall, color: Colors.textSecondary },
  decisionMeta: { flexDirection: 'row', justifyContent: 'space-between' },
  decisionAgents: { ...Typography.labelSmall, color: Colors.gold[500] },
  decisionDate: { ...Typography.labelSmall, color: Colors.textMuted },
  conveneBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, backgroundColor: Colors.gold[500],
    borderRadius: BorderRadius.full, paddingVertical: Spacing.base,
    marginTop: Spacing.md,
  },
  conveneText: { ...Typography.titleSmall, color: Colors.navy[900], fontWeight: '700' },
});
