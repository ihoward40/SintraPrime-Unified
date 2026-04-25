import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import {
  Camera,
  Upload,
  Search,
  FileText,
  Shield,
  ChevronRight,
  Clock,
} from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius, Shadow } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';
import { Document, DocumentCategory } from '@api/documents';
import { formatDate, formatFileSize } from '@utils/formatting';

const MOCK_DOCS: Document[] = [
  { id: 'd1', title: 'Employment Contract 2023', category: 'legal', mimeType: 'application/pdf', size: 245760, createdAt: '2026-01-15', updatedAt: '2026-01-15', tags: ['employment', 'contract'], isEncrypted: true, caseId: 'case-001' },
  { id: 'd2', title: 'Tax Return 2025', category: 'tax', mimeType: 'application/pdf', size: 512000, createdAt: '2026-03-10', updatedAt: '2026-03-10', tags: ['tax', '2025'], isEncrypted: true },
  { id: 'd3', title: 'Passport Copy', category: 'identity', mimeType: 'image/jpeg', size: 1048576, createdAt: '2025-11-20', updatedAt: '2025-11-20', tags: ['identity', 'passport'], isEncrypted: true },
  { id: 'd4', title: 'Medical Power of Attorney', category: 'legal', mimeType: 'application/pdf', size: 98304, createdAt: '2026-02-01', updatedAt: '2026-02-01', tags: ['medical', 'poa'], isEncrypted: true },
];

const CATEGORY_COLORS: Record<DocumentCategory, string> = {
  legal: Colors.gold[500],
  financial: Colors.success,
  identity: Colors.info,
  medical: Colors.error,
  real_estate: Colors.warning,
  tax: Colors.gold[400],
  contract: Colors.gold[500],
  court_filing: Colors.error,
  other: Colors.textMuted,
};

const CATEGORIES: { id: DocumentCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'legal', label: 'Legal' },
  { id: 'financial', label: 'Financial' },
  { id: 'tax', label: 'Tax' },
  { id: 'identity', label: 'Identity' },
];

export default function VaultScreen() {
  const navigation = useNavigation<any>();
  const [category, setCategory] = useState<DocumentCategory | 'all'>('all');

  const filtered = category === 'all'
    ? MOCK_DOCS
    : MOCK_DOCS.filter((d) => d.category === category);

  const totalSize = MOCK_DOCS.reduce((s, d) => s + d.size, 0);

  return (
    <View style={styles.container}>
      <GradientHeader
        title="Secure Vault"
        subtitle={`${MOCK_DOCS.length} documents · ${formatFileSize(totalSize)}`}
        rightAction={
          <TouchableOpacity style={styles.searchBtn}>
            <Search size={18} color={Colors.textSecondary} strokeWidth={1.5} />
          </TouchableOpacity>
        }
      />

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {/* Action buttons */}
          <View style={styles.actionRow}>
            <TouchableOpacity
              onPress={() => navigation.navigate('Scanner')}
              style={styles.actionBtn}
            >
              <View style={[styles.actionIcon, { backgroundColor: Colors.gold[500] + '20' }]}>
                <Camera size={22} color={Colors.gold[500]} strokeWidth={1.5} />
              </View>
              <Text style={styles.actionLabel}>Scan Document</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionBtn}>
              <View style={[styles.actionIcon, { backgroundColor: Colors.info + '20' }]}>
                <Upload size={22} color={Colors.info} strokeWidth={1.5} />
              </View>
              <Text style={styles.actionLabel}>Upload File</Text>
            </TouchableOpacity>
          </View>

          {/* Security badge */}
          <View style={styles.securityBadge}>
            <Shield size={14} color={Colors.success} strokeWidth={1.5} />
            <Text style={styles.securityText}>
              All documents are end-to-end encrypted with AES-256
            </Text>
          </View>

          {/* Category filter */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.filterRow}
          >
            {CATEGORIES.map((cat) => (
              <TouchableOpacity
                key={cat.id}
                onPress={() => setCategory(cat.id)}
                style={[styles.catChip, category === cat.id && styles.catChipActive]}
              >
                <Text style={[styles.catText, category === cat.id && styles.catTextActive]}>
                  {cat.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Documents */}
          <View style={styles.docList}>
            {filtered.map((doc) => (
              <TouchableOpacity
                key={doc.id}
                onPress={() =>
                  navigation.navigate('DocumentViewer', {
                    documentId: doc.id,
                    documentTitle: doc.title,
                    uri: '',
                  })
                }
                activeOpacity={0.85}
                style={styles.docItem}
              >
                <View style={[styles.docIconWrap, { backgroundColor: CATEGORY_COLORS[doc.category] + '20' }]}>
                  <FileText size={20} color={CATEGORY_COLORS[doc.category]} strokeWidth={1.5} />
                </View>
                <View style={styles.docInfo}>
                  <Text style={styles.docTitle} numberOfLines={1}>{doc.title}</Text>
                  <View style={styles.docMeta}>
                    <Text style={styles.docCategory}>{doc.category.replace('_', ' ')}</Text>
                    <Text style={styles.docSeparator}>·</Text>
                    <Text style={styles.docSize}>{formatFileSize(doc.size)}</Text>
                    <Text style={styles.docSeparator}>·</Text>
                    <Clock size={10} color={Colors.textMuted} strokeWidth={2} />
                    <Text style={styles.docDate}>{formatDate(doc.createdAt, 'MMM d')}</Text>
                  </View>
                  {doc.tags.length > 0 && (
                    <View style={styles.tagsRow}>
                      {doc.tags.slice(0, 3).map((tag) => (
                        <View key={tag} style={styles.tag}>
                          <Text style={styles.tagText}>{tag}</Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>
                {doc.isEncrypted && (
                  <Shield size={12} color={Colors.success} strokeWidth={2} />
                )}
                <ChevronRight size={14} color={Colors.textMuted} strokeWidth={1.5} />
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  searchBtn: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: Colors.surface, alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  scroll: { padding: Spacing.base, gap: Spacing.base, paddingBottom: Spacing['3xl'] },
  actionRow: { flexDirection: 'row', gap: Spacing.md },
  actionBtn: {
    flex: 1, alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
  },
  actionIcon: { width: 52, height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  actionLabel: { ...Typography.labelMedium, color: Colors.textSecondary },
  securityBadge: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.success + '10',
    borderRadius: BorderRadius.full, paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm,
    borderWidth: 1, borderColor: Colors.success + '30',
    alignSelf: 'flex-start',
  },
  securityText: { ...Typography.labelSmall, color: Colors.success },
  filterRow: { gap: Spacing.sm },
  catChip: {
    paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full, backgroundColor: Colors.surface,
    borderWidth: 1, borderColor: Colors.border,
  },
  catChipActive: { backgroundColor: Colors.gold[500] + '20', borderColor: Colors.gold[500] },
  catText: { ...Typography.labelSmall, color: Colors.textMuted },
  catTextActive: { color: Colors.gold[500], fontWeight: '600' },
  docList: { gap: Spacing.sm },
  docItem: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
  },
  docIconWrap: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  docInfo: { flex: 1 },
  docTitle: { ...Typography.bodyMedium, color: Colors.textPrimary, fontWeight: '500' },
  docMeta: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2, flexWrap: 'wrap' },
  docCategory: { ...Typography.labelSmall, color: Colors.textMuted, textTransform: 'capitalize' },
  docSeparator: { color: Colors.textMuted, fontSize: 10 },
  docSize: { ...Typography.labelSmall, color: Colors.textMuted },
  docDate: { ...Typography.labelSmall, color: Colors.textMuted },
  tagsRow: { flexDirection: 'row', gap: 4, marginTop: 4, flexWrap: 'wrap' },
  tag: { paddingHorizontal: 6, paddingVertical: 2, backgroundColor: Colors.border, borderRadius: 4 },
  tagText: { ...Typography.labelSmall, color: Colors.textMuted, fontSize: 9 },
});
