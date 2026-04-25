import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRoute, useNavigation, RouteProp } from '@react-navigation/native';
import {
  Clock,
  FileText,
  MessageSquare,
  Zap,
  Calendar,
  Search,
  Edit3,
  ArrowRight,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { LegalStackParamList } from '@navigation/types';
import { useCaseStore } from '@store/caseStore';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import {
  formatDate,
  formatDeadlineCountdown,
  getDaysUntil,
  formatCaseType,
} from '@utils/formatting';
import GradientHeader from '@components/common/GradientHeader';
import GoldCard from '@components/common/GoldCard';

type RouteType = RouteProp<LegalStackParamList, 'CaseDetail'>;

const TABS = ['Overview', 'Timeline', 'Documents', 'Notes'] as const;

export default function CaseDetailScreen() {
  const route = useRoute<RouteType>();
  const navigation = useNavigation<any>();
  const { caseId } = route.params;
  const { getCaseById } = useCaseStore();
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('Overview');

  const case_ = getCaseById(caseId);
  if (!case_) {
    return (
      <View style={styles.container}>
        <GradientHeader title="Case Not Found" showBack />
      </View>
    );
  }

  const daysUntil = case_.deadlineDate ? getDaysUntil(case_.deadlineDate) : null;
  const isUrgent = daysUntil !== null && daysUntil <= 7;

  const EVENT_TYPE_COLORS: Record<string, string> = {
    filing: Colors.info,
    hearing: Colors.warning,
    deadline: Colors.error,
    note: Colors.textMuted,
    decision: Colors.success,
  };

  return (
    <View style={styles.container}>
      <GradientHeader
        title={case_.title}
        subtitle={`Case #${case_.caseNumber}`}
        showBack
        rightAction={
          <TouchableOpacity style={styles.editBtn}>
            <Edit3 size={18} color={Colors.gold[500]} strokeWidth={1.5} />
          </TouchableOpacity>
        }
      >
        {/* Status + deadline */}
        <View style={styles.headerMeta}>
          <View style={[styles.statusBadge, { backgroundColor: Colors.success + '20' }]}>
            <View style={[styles.statusDot, { backgroundColor: Colors.success }]} />
            <Text style={[styles.statusText, { color: Colors.success }]}>
              {case_.status.toUpperCase()}
            </Text>
          </View>
          {case_.deadlineDate && (
            <View style={[styles.deadlineBadge, isUrgent && styles.deadlineBadgeUrgent]}>
              <Clock size={12} color={isUrgent ? Colors.error : Colors.warning} strokeWidth={2} />
              <Text style={[styles.deadlineText, isUrgent && styles.deadlineTextUrgent]}>
                {formatDeadlineCountdown(case_.deadlineDate)}
              </Text>
            </View>
          )}
          <View style={styles.typeBadge}>
            <Text style={styles.typeText}>{formatCaseType(case_.type)}</Text>
          </View>
        </View>

        {/* Tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabs}>
          {TABS.map((tab) => (
            <TouchableOpacity
              key={tab}
              onPress={() => setActiveTab(tab)}
              style={[styles.tab, activeTab === tab && styles.tabActive]}
            >
              <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                {tab}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </GradientHeader>

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {activeTab === 'Overview' && (
            <View style={styles.section}>
              {/* Summary */}
              <GoldCard>
                <Text style={styles.fieldLabel}>Case Summary</Text>
                <Text style={styles.summaryText}>{case_.summary}</Text>
              </GoldCard>

              {/* Details grid */}
              <View style={styles.detailsGrid}>
                {case_.court && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Court</Text>
                    <Text style={styles.detailValue}>{case_.court}</Text>
                  </View>
                )}
                {case_.judge && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Judge</Text>
                    <Text style={styles.detailValue}>{case_.judge}</Text>
                  </View>
                )}
                {case_.opposingParty && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Opposing Party</Text>
                    <Text style={styles.detailValue}>{case_.opposingParty}</Text>
                  </View>
                )}
                {case_.nextHearing && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Next Hearing</Text>
                    <Text style={[styles.detailValue, { color: Colors.warning }]}>
                      {formatDate(case_.nextHearing)}
                    </Text>
                  </View>
                )}
                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Priority</Text>
                  <Text style={[styles.detailValue, {
                    color: case_.priority === 'high' ? Colors.error : case_.priority === 'medium' ? Colors.warning : Colors.success
                  }]}>
                    {case_.priority.charAt(0).toUpperCase() + case_.priority.slice(1)}
                  </Text>
                </View>
                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Opened</Text>
                  <Text style={styles.detailValue}>{formatDate(case_.openedDate)}</Text>
                </View>
              </View>

              {/* Actions */}
              <Text style={styles.actionsHeader}>Quick Actions</Text>
              <View style={styles.actionsGrid}>
                <TouchableOpacity
                  onPress={() => navigation.navigate('MotionDrafter', { caseId: case_.id })}
                  style={styles.actionBtn}
                >
                  <Edit3 size={18} color={Colors.gold[500]} strokeWidth={1.5} />
                  <Text style={styles.actionText}>Draft Motion</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => navigation.navigate('CaseLawSearch', { query: case_.title })}
                  style={styles.actionBtn}
                >
                  <Search size={18} color={Colors.info} strokeWidth={1.5} />
                  <Text style={styles.actionText}>Research Precedent</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.actionBtn}>
                  <Calendar size={18} color={Colors.warning} strokeWidth={1.5} />
                  <Text style={styles.actionText}>Court Schedule</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => navigation.navigate('AI', {
                    screen: 'AIAssistant',
                    params: { initialQuery: `Help me with case: ${case_.title}` },
                  })}
                  style={styles.actionBtn}
                >
                  <Zap size={18} color={Colors.success} strokeWidth={1.5} />
                  <Text style={styles.actionText}>Ask AI Counsel</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {activeTab === 'Timeline' && (
            <View style={styles.section}>
              {case_.events.length === 0 && (
                <View style={styles.empty}>
                  <Text style={styles.emptyText}>No timeline events yet</Text>
                </View>
              )}
              {case_.events.map((event, i) => (
                <View key={event.id} style={styles.timelineItem}>
                  <View style={styles.timelineLine}>
                    <View
                      style={[
                        styles.timelineDot,
                        { backgroundColor: EVENT_TYPE_COLORS[event.type] ?? Colors.textMuted },
                      ]}
                    />
                    {i < case_.events.length - 1 && (
                      <View style={styles.timelineConnector} />
                    )}
                  </View>
                  <View style={styles.timelineContent}>
                    <Text style={styles.timelineDate}>{formatDate(event.date)}</Text>
                    <Text style={styles.timelineTitle}>{event.title}</Text>
                    <Text style={styles.timelineDesc}>{event.description}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {activeTab === 'Documents' && (
            <View style={styles.section}>
              <GoldCard>
                <View style={styles.docCount}>
                  <FileText size={32} color={Colors.gold[500]} strokeWidth={1} />
                  <Text style={styles.docCountNum}>{case_.documentCount}</Text>
                  <Text style={styles.docCountLabel}>Documents</Text>
                </View>
              </GoldCard>
              <TouchableOpacity
                onPress={() => navigation.navigate('Documents', {
                  screen: 'Vault',
                  params: { caseId: case_.id },
                })}
                style={styles.viewDocsBtn}
              >
                <Text style={styles.viewDocsBtnText}>View All Documents</Text>
                <ArrowRight size={16} color={Colors.gold[500]} strokeWidth={2} />
              </TouchableOpacity>
            </View>
          )}

          {activeTab === 'Notes' && (
            <View style={styles.section}>
              <View style={styles.empty}>
                <MessageSquare size={48} color={Colors.textMuted} strokeWidth={1} />
                <Text style={styles.emptyText}>No notes yet</Text>
              </View>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  editBtn: {
    padding: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  headerMeta: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap', marginBottom: Spacing.sm },
  statusBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: Spacing.sm, paddingVertical: 4,
    borderRadius: BorderRadius.full,
  },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
  statusText: { ...Typography.labelSmall, fontWeight: '700', fontSize: 10 },
  deadlineBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: Spacing.sm, paddingVertical: 4,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.warning + '20',
  },
  deadlineBadgeUrgent: { backgroundColor: Colors.error + '20' },
  deadlineText: { ...Typography.labelSmall, color: Colors.warning, fontWeight: '600', fontSize: 10 },
  deadlineTextUrgent: { color: Colors.error },
  typeBadge: {
    paddingHorizontal: Spacing.sm, paddingVertical: 4,
    backgroundColor: Colors.border, borderRadius: BorderRadius.full,
  },
  typeText: { ...Typography.labelSmall, color: Colors.textSecondary, fontSize: 10 },
  tabs: { marginTop: Spacing.sm },
  tab: {
    paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm,
    marginRight: Spacing.xs, borderRadius: BorderRadius.full,
  },
  tabActive: { backgroundColor: Colors.gold[500] + '20' },
  tabText: { ...Typography.labelMedium, color: Colors.textMuted },
  tabTextActive: { color: Colors.gold[500], fontWeight: '600' },
  scroll: { paddingBottom: Spacing['3xl'] },
  section: { padding: Spacing.base, gap: Spacing.md },
  fieldLabel: { ...Typography.labelSmall, color: Colors.textMuted, marginBottom: Spacing.xs, textTransform: 'uppercase' },
  summaryText: { ...Typography.bodyMedium, color: Colors.textSecondary, lineHeight: 24 },
  detailsGrid: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: 'hidden',
  },
  detailItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  detailLabel: { ...Typography.bodySmall, color: Colors.textMuted },
  detailValue: { ...Typography.bodySmall, color: Colors.textPrimary, fontWeight: '500', flex: 1, textAlign: 'right' },
  actionsHeader: { ...Typography.titleSmall, color: Colors.textPrimary },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  actionBtn: {
    flex: 1, minWidth: '46%',
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl, padding: Spacing.base,
    borderWidth: 1, borderColor: Colors.border,
  },
  actionText: { ...Typography.labelMedium, color: Colors.textSecondary },
  timelineItem: { flexDirection: 'row', gap: Spacing.md },
  timelineLine: { alignItems: 'center', width: 20 },
  timelineDot: { width: 12, height: 12, borderRadius: 6, marginTop: 4 },
  timelineConnector: { width: 2, flex: 1, backgroundColor: Colors.border, marginTop: 4 },
  timelineContent: { flex: 1, paddingBottom: Spacing.xl },
  timelineDate: { ...Typography.labelSmall, color: Colors.textMuted, marginBottom: 2 },
  timelineTitle: { ...Typography.titleSmall, color: Colors.textPrimary, marginBottom: 4 },
  timelineDesc: { ...Typography.bodySmall, color: Colors.textSecondary },
  docCount: { alignItems: 'center', gap: Spacing.sm },
  docCountNum: { ...Typography.headlineLarge, color: Colors.textPrimary },
  docCountLabel: { ...Typography.bodyMedium, color: Colors.textSecondary },
  viewDocsBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, padding: Spacing.base,
    borderWidth: 1.5, borderColor: Colors.gold[500],
    borderRadius: BorderRadius.full,
  },
  viewDocsBtnText: { ...Typography.labelLarge, color: Colors.gold[500] },
  empty: { alignItems: 'center', paddingVertical: Spacing['3xl'], gap: Spacing.md },
  emptyText: { ...Typography.bodyMedium, color: Colors.textMuted },
});
