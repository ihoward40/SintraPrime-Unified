import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Zap, Copy, Share2, Download } from 'lucide-react-native';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';
import LoadingOverlay from '@components/common/LoadingOverlay';

const MOTION_TYPES = [
  'Motion to Dismiss',
  'Motion for Summary Judgment',
  'Motion to Compel Discovery',
  'Motion for Continuance',
  'Motion in Limine',
  'Motion to Strike',
  'Motion for Sanctions',
  'Temporary Restraining Order',
];

const MOCK_DRAFT = `IN THE UNITED STATES DISTRICT COURT
FOR THE SOUTHERN DISTRICT OF NEW YORK

CASE NO. CV-2026-00147

PLAINTIFF'S MOTION FOR SUMMARY JUDGMENT

Plaintiff, by and through undersigned counsel, respectfully moves this Court for summary judgment pursuant to Federal Rule of Civil Procedure 56, and states as follows:

INTRODUCTION

Plaintiff brings this action for wrongful termination and employment discrimination under Title VII of the Civil Rights Act of 1964 and the Americans with Disabilities Act. The undisputed material facts establish that Plaintiff is entitled to judgment as a matter of law.

STATEMENT OF UNDISPUTED MATERIAL FACTS

1. Plaintiff was employed by Defendant from January 15, 2023 through December 1, 2025.
2. Plaintiff consistently received satisfactory performance reviews throughout their tenure.
3. Defendant terminated Plaintiff's employment without legitimate business justification.
4. Similarly-situated employees outside Plaintiff's protected class were treated more favorably.

LEGAL ARGUMENT

I. SUMMARY JUDGMENT STANDARD

Summary judgment is appropriate when "there is no genuine dispute as to any material fact and the movant is entitled to judgment as a matter of law." Fed. R. Civ. P. 56(a). See Anderson v. Liberty Lobby, Inc., 477 U.S. 242, 247-48 (1986).

II. PLAINTIFF ESTABLISHES A PRIMA FACIE CASE OF DISCRIMINATION

Under the burden-shifting framework of McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973), Plaintiff establishes a prima facie case by demonstrating: (1) membership in a protected class; (2) qualification for the position; (3) adverse employment action; and (4) circumstances giving rise to an inference of discrimination.

CONCLUSION

For the foregoing reasons, Plaintiff respectfully requests that this Court grant summary judgment in Plaintiff's favor on all claims.

Respectfully submitted,
SintraPrime AI Counsel
[Date]

[AI Generated — Review by licensed attorney required before filing]`;

export default function MotionDrafterScreen() {
  const [selectedType, setSelectedType] = useState<string>('');
  const [jurisdiction, setJurisdiction] = useState('');
  const [keyFacts, setKeyFacts] = useState('');
  const [draft, setDraft] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async () => {
    if (!selectedType) {
      Alert.alert('Select Motion Type', 'Please select a motion type to continue.');
      return;
    }
    setIsLoading(true);
    await new Promise((r) => setTimeout(r, 2500)); // Simulate AI generation
    setDraft(MOCK_DRAFT);
    setIsLoading(false);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  };

  const handleCopy = async () => {
    await Clipboard.setStringAsync(draft);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    Alert.alert('Copied', 'Motion draft copied to clipboard');
  };

  return (
    <View style={styles.container}>
      <GradientHeader title="AI Motion Drafter" subtitle="Professional legal motions in minutes" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {!draft ? (
            <View style={styles.form}>
              {/* Motion type */}
              <Text style={styles.label}>Motion Type</Text>
              <View style={styles.typeGrid}>
                {MOTION_TYPES.map((type) => (
                  <TouchableOpacity
                    key={type}
                    onPress={() => setSelectedType(type)}
                    style={[
                      styles.typeChip,
                      selectedType === type && styles.typeChipActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.typeChipText,
                        selectedType === type && styles.typeChipTextActive,
                      ]}
                    >
                      {type}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Jurisdiction */}
              <Text style={styles.label}>Jurisdiction</Text>
              <TextInput
                style={styles.input}
                value={jurisdiction}
                onChangeText={setJurisdiction}
                placeholder="e.g. U.S. District Court, S.D.N.Y."
                placeholderTextColor={Colors.textMuted}
              />

              {/* Key facts */}
              <Text style={styles.label}>Key Arguments & Facts</Text>
              <TextInput
                style={[styles.input, styles.inputMulti]}
                value={keyFacts}
                onChangeText={setKeyFacts}
                placeholder="Describe the key facts and arguments for this motion..."
                placeholderTextColor={Colors.textMuted}
                multiline
                numberOfLines={5}
                textAlignVertical="top"
              />

              {/* Generate */}
              <TouchableOpacity
                onPress={handleGenerate}
                activeOpacity={0.85}
                style={styles.generateBtn}
              >
                <Zap size={18} color={Colors.navy[900]} strokeWidth={2} />
                <Text style={styles.generateText}>Generate Motion Draft</Text>
              </TouchableOpacity>

              <Text style={styles.disclaimer}>
                ⚠️ AI-generated drafts require review by a licensed attorney before filing.
              </Text>
            </View>
          ) : (
            <View style={styles.draftContainer}>
              <View style={styles.draftActions}>
                <TouchableOpacity onPress={handleCopy} style={styles.draftActionBtn}>
                  <Copy size={16} color={Colors.gold[500]} strokeWidth={1.5} />
                  <Text style={styles.draftActionText}>Copy</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.draftActionBtn}>
                  <Share2 size={16} color={Colors.info} strokeWidth={1.5} />
                  <Text style={[styles.draftActionText, { color: Colors.info }]}>Share</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.draftActionBtn}>
                  <Download size={16} color={Colors.success} strokeWidth={1.5} />
                  <Text style={[styles.draftActionText, { color: Colors.success }]}>Save PDF</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setDraft('')}
                  style={[styles.draftActionBtn, { borderColor: Colors.error + '40' }]}
                >
                  <Text style={[styles.draftActionText, { color: Colors.error }]}>Restart</Text>
                </TouchableOpacity>
              </View>
              <View style={styles.draftBox}>
                <Text style={styles.draftText}>{draft}</Text>
              </View>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
      <LoadingOverlay visible={isLoading} message="AI is drafting your motion..." />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scroll: { padding: Spacing.base, paddingBottom: Spacing['4xl'] },
  form: { gap: Spacing.base },
  label: { ...Typography.labelMedium, color: Colors.textSecondary, marginBottom: -4 },
  typeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  typeChip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  typeChipActive: { backgroundColor: Colors.gold[500] + '20', borderColor: Colors.gold[500] },
  typeChipText: { ...Typography.labelSmall, color: Colors.textSecondary },
  typeChipTextActive: { color: Colors.gold[500], fontWeight: '600' },
  input: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  inputMulti: { height: 120, paddingTop: Spacing.base },
  generateBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm,
    backgroundColor: Colors.gold[500],
    borderRadius: BorderRadius.full,
    paddingVertical: Spacing.base,
    marginTop: Spacing.sm,
  },
  generateText: { ...Typography.titleSmall, color: Colors.navy[900], fontWeight: '700' },
  disclaimer: { ...Typography.bodySmall, color: Colors.textMuted, textAlign: 'center', lineHeight: 18 },
  draftContainer: { gap: Spacing.base },
  draftActions: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap' },
  draftActionBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.surface,
    borderWidth: 1, borderColor: Colors.gold[500] + '40',
  },
  draftActionText: { ...Typography.labelSmall, color: Colors.gold[500] },
  draftBox: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  draftText: {
    ...Typography.monospace,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
});
