import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import {
  Scale,
  Users,
  Home,
  Globe,
  Building2,
  FileText,
  Briefcase,
  Heart,
  Search,
  Plus,
} from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { useCaseStore } from '@store/caseStore';
import CaseCard from '@components/legal/CaseCard';
import PracticeAreaCard from '@components/legal/PracticeAreaCard';
import GradientHeader from '@components/common/GradientHeader';

const PRACTICE_AREAS = [
  { id: 'employment', title: 'Employment Law', icon: <Briefcase size={22} color={Colors.gold[500]} strokeWidth={1.5} />, desc: 'Wrongful termination, discrimination, wage disputes' },
  { id: 'family', title: 'Family Law', icon: <Heart size={22} color={Colors.error} strokeWidth={1.5} />, desc: 'Divorce, custody, child support, adoption' },
  { id: 'immigration', title: 'Immigration', icon: <Globe size={22} color={Colors.info} strokeWidth={1.5} />, desc: 'Visas, green cards, citizenship, deportation defense' },
  { id: 'corporate', title: 'Corporate Law', icon: <Building2 size={22} color={Colors.warning} strokeWidth={1.5} />, desc: 'Business formation, contracts, mergers, compliance' },
  { id: 'real_estate', title: 'Real Estate', icon: <Home size={22} color={Colors.success} strokeWidth={1.5} />, desc: 'Transactions, disputes, landlord-tenant, zoning' },
  { id: 'trust_estate', title: 'Trusts & Estates', icon: <FileText size={22} color={Colors.gold[500]} strokeWidth={1.5} />, desc: 'Will drafting, trust administration, probate' },
  { id: 'civil', title: 'Civil Litigation', icon: <Scale size={22} color={Colors.textSecondary} strokeWidth={1.5} />, desc: 'Disputes, torts, class actions, appeals' },
];

export default function LegalHubScreen() {
  const navigation = useNavigation<any>();
  const { cases, getActiveCases } = useCaseStore();
  const [activeTab, setActiveTab] = useState<'cases' | 'areas'>('cases');
  const activeCases = getActiveCases();

  return (
    <View style={styles.container}>
      <GradientHeader
        title="Legal Hub"
        subtitle="Powered by SintraPrime AI"
        rightAction={
          <View style={styles.headerActions}>
            <TouchableOpacity
              onPress={() => navigation.navigate('CaseLawSearch')}
              style={styles.headerBtn}
            >
              <Search size={20} color={Colors.textSecondary} strokeWidth={1.5} />
            </TouchableOpacity>
            <TouchableOpacity style={[styles.headerBtn, styles.addBtn]}>
              <Plus size={20} color={Colors.navy[900]} strokeWidth={2} />
            </TouchableOpacity>
          </View>
        }
      >
        {/* Tabs */}
        <View style={styles.tabs}>
          {(['cases', 'areas'] as const).map((tab) => (
            <TouchableOpacity
              key={tab}
              onPress={() => setActiveTab(tab)}
              style={[styles.tab, activeTab === tab && styles.tabActive]}
            >
              <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                {tab === 'cases' ? `Cases (${activeCases.length})` : 'Practice Areas'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </GradientHeader>

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {activeTab === 'cases' ? (
            <View style={styles.section}>
              {cases.map((c) => (
                <CaseCard
                  key={c.id}
                  case_={c}
                  onPress={() =>
                    navigation.navigate('CaseDetail', { caseId: c.id, caseTitle: c.title })
                  }
                  style={styles.caseCard}
                />
              ))}
              {cases.length === 0 && (
                <View style={styles.empty}>
                  <Scale size={48} color={Colors.textMuted} strokeWidth={1} />
                  <Text style={styles.emptyTitle}>No Cases Yet</Text>
                  <Text style={styles.emptySub}>Tap + to open your first case</Text>
                </View>
              )}
            </View>
          ) : (
            <View style={styles.section}>
              {PRACTICE_AREAS.map((area) => (
                <PracticeAreaCard
                  key={area.id}
                  title={area.title}
                  description={area.desc}
                  icon={area.icon}
                  caseCount={cases.filter((c) => c.type === area.id).length}
                  onPress={() => {}}
                  style={styles.areaCard}
                />
              ))}

              {/* AI Tools */}
              <Text style={styles.toolsHeader}>AI Legal Tools</Text>
              <TouchableOpacity
                onPress={() => navigation.navigate('MotionDrafter')}
                style={styles.toolItem}
              >
                <FileText size={18} color={Colors.gold[500]} strokeWidth={1.5} />
                <View style={styles.toolContent}>
                  <Text style={styles.toolTitle}>AI Motion Drafter</Text>
                  <Text style={styles.toolSub}>Generate professional legal motions in minutes</Text>
                </View>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => navigation.navigate('CaseLawSearch')}
                style={styles.toolItem}
              >
                <Search size={18} color={Colors.info} strokeWidth={1.5} />
                <View style={styles.toolContent}>
                  <Text style={styles.toolTitle}>Case Law Search</Text>
                  <Text style={styles.toolSub}>Search 10M+ precedents with AI ranking</Text>
                </View>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => navigation.navigate('TrustLaw')}
                style={styles.toolItem}
              >
                <Scale size={18} color={Colors.success} strokeWidth={1.5} />
                <View style={styles.toolContent}>
                  <Text style={styles.toolTitle}>Trust & Estate Planner</Text>
                  <Text style={styles.toolSub}>AI-guided trust creation and estate planning</Text>
                </View>
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingBottom: Spacing['3xl'] },
  headerActions: { flexDirection: 'row', gap: Spacing.sm },
  headerBtn: {
    width: 36, height: 36,
    borderRadius: 12,
    backgroundColor: Colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  addBtn: {
    backgroundColor: Colors.gold[500],
    borderColor: Colors.gold[500],
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: Colors.navy[950],
    borderRadius: BorderRadius.lg,
    padding: 3,
  },
  tab: {
    flex: 1,
    paddingVertical: Spacing.sm,
    alignItems: 'center',
    borderRadius: BorderRadius.md,
  },
  tabActive: {
    backgroundColor: Colors.surface,
  },
  tabText: {
    ...Typography.labelMedium,
    color: Colors.textMuted,
  },
  tabTextActive: {
    color: Colors.gold[500],
    fontWeight: '600',
  },
  section: { padding: Spacing.base, gap: Spacing.md },
  caseCard: {},
  areaCard: {},
  empty: { alignItems: 'center', paddingVertical: Spacing['4xl'], gap: Spacing.md },
  emptyTitle: { ...Typography.titleLarge, color: Colors.textPrimary },
  emptySub: { ...Typography.bodyMedium, color: Colors.textSecondary },
  toolsHeader: { ...Typography.titleMedium, color: Colors.textPrimary, marginTop: Spacing.md },
  toolItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  toolContent: { flex: 1 },
  toolTitle: { ...Typography.titleSmall, color: Colors.textPrimary },
  toolSub: { ...Typography.bodySmall, color: Colors.textSecondary, marginTop: 2 },
});
