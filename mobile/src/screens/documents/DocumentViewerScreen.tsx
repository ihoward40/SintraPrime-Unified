import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native';
import { Share2, Download, Trash2, FileText } from 'lucide-react-native';
import { DocumentsStackParamList } from '@navigation/types';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';

type RouteType = RouteProp<DocumentsStackParamList, 'DocumentViewer'>;

export default function DocumentViewerScreen() {
  const route = useRoute<RouteType>();
  const { documentTitle, documentId } = route.params;

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader
        title={documentTitle}
        subtitle="Secure Document Viewer"
        showBack
        rightAction={
          <View style={styles.actions}>
            <TouchableOpacity style={styles.actionBtn}>
              <Share2 size={16} color={Colors.textSecondary} strokeWidth={1.5} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionBtn}>
              <Download size={16} color={Colors.textSecondary} strokeWidth={1.5} />
            </TouchableOpacity>
          </View>
        }
      />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <View style={styles.container}>
          <FileText size={64} color={Colors.gold[500]} strokeWidth={0.8} />
          <Text style={styles.placeholder}>Document Viewer</Text>
          <Text style={styles.placeholderSub}>
            PDF and image viewer renders here. Integration with expo-document-viewer for production.
          </Text>
          <TouchableOpacity style={styles.deleteBtn}>
            <Trash2 size={16} color={Colors.error} strokeWidth={1.5} />
            <Text style={styles.deleteText}>Delete Document</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: Spacing.sm },
  actionBtn: {
    width: 34, height: 34, borderRadius: 10,
    backgroundColor: Colors.surface,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  container: {
    flex: 1, alignItems: 'center', justifyContent: 'center',
    padding: Spacing['2xl'], gap: Spacing.base,
  },
  placeholder: { ...Typography.titleLarge, color: Colors.textPrimary },
  placeholderSub: { ...Typography.bodyMedium, color: Colors.textSecondary, textAlign: 'center', lineHeight: 24 },
  deleteBtn: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    marginTop: Spacing.xl, padding: Spacing.base,
  },
  deleteText: { ...Typography.labelMedium, color: Colors.error },
});
