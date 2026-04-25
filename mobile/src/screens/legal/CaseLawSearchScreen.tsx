import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Search, X, Sliders } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';
import CaseLawResult from '@components/legal/CaseLawResult';
import { CaseLawResult as CaseLawResultType } from '@api/cases';

const MOCK_RESULTS: CaseLawResultType[] = [
  {
    id: 'cl-001',
    title: 'McDonnell Douglas Corp. v. Green',
    court: 'U.S. Supreme Court',
    date: '1973-05-14',
    citation: '411 U.S. 792 (1973)',
    summary: 'Established the burden-shifting framework for Title VII employment discrimination cases. The plaintiff must first establish a prima facie case of discrimination.',
    relevanceScore: 0.96,
    url: 'https://supreme.justia.com/cases/federal/us/411/792/',
  },
  {
    id: 'cl-002',
    title: 'Burlington Northern & Santa Fe Ry. v. White',
    court: 'U.S. Supreme Court',
    date: '2006-06-22',
    citation: '548 U.S. 53 (2006)',
    summary: 'Defined the scope of anti-retaliation provisions under Title VII. Retaliation includes any action that would deter a reasonable employee from reporting discrimination.',
    relevanceScore: 0.89,
    url: '',
  },
  {
    id: 'cl-003',
    title: 'Faragher v. City of Boca Raton',
    court: 'U.S. Supreme Court',
    date: '1998-06-26',
    citation: '524 U.S. 775 (1998)',
    summary: 'Addressed employer liability for supervisor harassment under Title VII, establishing the affirmative defense for hostile work environment claims.',
    relevanceScore: 0.78,
    url: '',
  },
];

const SUGGESTED_QUERIES = [
  'Wrongful termination precedents 2024',
  'Hostile work environment standard',
  'Summary judgment employment discrimination',
  'Title VII retaliation elements',
];

export default function CaseLawSearchScreen() {
  const navigation = useNavigation();
  const route = useRoute<any>();
  const [query, setQuery] = useState(route.params?.query ?? '');
  const [results, setResults] = useState<CaseLawResultType[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (q?: string) => {
    const searchQuery = q ?? query;
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setHasSearched(false);
    await Haptics.selectionAsync();
    await new Promise((r) => setTimeout(r, 1500));
    setResults(MOCK_RESULTS);
    setIsSearching(false);
    setHasSearched(true);
  };

  return (
    <View style={styles.container}>
      <GradientHeader title="Case Law Search" subtitle="10M+ precedents • AI-ranked" showBack>
        <View style={styles.searchRow}>
          <View style={styles.searchBox}>
            <Search size={18} color={Colors.textMuted} strokeWidth={1.5} />
            <TextInput
              style={styles.searchInput}
              value={query}
              onChangeText={setQuery}
              placeholder="Search cases, statutes, legal topics..."
              placeholderTextColor={Colors.textMuted}
              returnKeyType="search"
              onSubmitEditing={() => handleSearch()}
              autoFocus={!route.params?.query}
            />
            {query.length > 0 && (
              <TouchableOpacity onPress={() => { setQuery(''); setResults([]); setHasSearched(false); }}>
                <X size={16} color={Colors.textMuted} strokeWidth={2} />
              </TouchableOpacity>
            )}
          </View>
          <TouchableOpacity style={styles.filterBtn}>
            <Sliders size={18} color={Colors.gold[500]} strokeWidth={1.5} />
          </TouchableOpacity>
        </View>
      </GradientHeader>

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Suggestions */}
          {!hasSearched && !isSearching && (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>Suggested Searches</Text>
              <View style={styles.chipRow}>
                {SUGGESTED_QUERIES.map((q) => (
                  <TouchableOpacity
                    key={q}
                    onPress={() => { setQuery(q); handleSearch(q); }}
                    style={styles.chip}
                  >
                    <Text style={styles.chipText}>{q}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {/* Loading */}
          {isSearching && (
            <View style={styles.loadingCenter}>
              <ActivityIndicator size="large" color={Colors.gold[500]} />
              <Text style={styles.loadingText}>Searching case law...</Text>
            </View>
          )}

          {/* Results */}
          {hasSearched && !isSearching && (
            <View style={styles.section}>
              <Text style={styles.resultsCount}>
                {results.length} results for "{query}"
              </Text>
              {results.map((result) => (
                <CaseLawResult
                  key={result.id}
                  result={result}
                  onPress={() => {}}
                />
              ))}
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  searchRow: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'center' },
  searchBox: {
    flex: 1, flexDirection: 'row', alignItems: 'center',
    backgroundColor: Colors.navy[950],
    borderRadius: BorderRadius.full,
    paddingHorizontal: Spacing.base,
    height: 44,
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  searchInput: { flex: 1, ...Typography.bodyMedium, color: Colors.textPrimary },
  filterBtn: {
    width: 44, height: 44,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.surface,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  scroll: { padding: Spacing.base, paddingBottom: Spacing['3xl'] },
  section: { gap: Spacing.md },
  sectionLabel: { ...Typography.labelMedium, color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  chip: {
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.full,
    borderWidth: 1, borderColor: Colors.border,
  },
  chipText: { ...Typography.labelSmall, color: Colors.textSecondary },
  loadingCenter: { alignItems: 'center', paddingVertical: Spacing['4xl'], gap: Spacing.base },
  loadingText: { ...Typography.bodyMedium, color: Colors.textMuted },
  resultsCount: { ...Typography.bodySmall, color: Colors.textMuted },
});
