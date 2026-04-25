import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Camera, CameraType, FlashMode } from 'expo-camera';
import { useNavigation } from '@react-navigation/native';
import { X, Zap, ZapOff, RotateCcw, Check, ScanLine } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';

const CATEGORIES = ['Legal', 'Financial', 'Identity', 'Medical', 'Tax', 'Other'];

export default function ScannerScreen() {
  const navigation = useNavigation();
  const cameraRef = useRef<Camera>(null);
  const [permission, requestPermission] = Camera.useCameraPermissions();
  const [flash, setFlash] = useState<FlashMode>(FlashMode.off);
  const [isProcessing, setIsProcessing] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('Legal');
  const [pageCount, setPageCount] = useState(0);

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.permissionContainer}>
        <ScanLine size={64} color={Colors.gold[500]} strokeWidth={1} />
        <Text style={styles.permissionTitle}>Camera Access Required</Text>
        <Text style={styles.permissionSub}>
          SintraPrime needs camera access to scan and digitize your documents.
        </Text>
        <TouchableOpacity onPress={requestPermission} style={styles.permissionBtn}>
          <Text style={styles.permissionBtnText}>Grant Camera Access</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.cancelLink}>
          <Text style={styles.cancelLinkText}>Cancel</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const handleCapture = async () => {
    if (!cameraRef.current || isProcessing) return;
    setIsProcessing(true);
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.9,
        base64: false,
        skipProcessing: false,
      });
      setCapturedPhoto(photo.uri);
      setPageCount((p) => p + 1);
    } catch (e) {
      Alert.alert('Error', 'Failed to capture photo');
    }
    setIsProcessing(false);
  };

  const handleSave = async () => {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    Alert.alert(
      'Document Scanned',
      `${pageCount} page(s) saved to your ${selectedCategory} vault.`,
      [{ text: 'OK', onPress: () => navigation.goBack() }],
    );
  };

  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        type={CameraType.back}
        flashMode={flash}
        ratio="4:3"
      />

      {/* Document edge overlay */}
      <View style={styles.overlay}>
        <View style={styles.cornerTL} />
        <View style={styles.cornerTR} />
        <View style={styles.cornerBL} />
        <View style={styles.cornerBR} />
      </View>

      {/* Top controls */}
      <SafeAreaView edges={['top']} style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconBtn}>
          <X size={22} color={Colors.textPrimary} strokeWidth={2} />
        </TouchableOpacity>
        <Text style={styles.topTitle}>
          Scan Document {pageCount > 0 && `(${pageCount} pages)`}
        </Text>
        <TouchableOpacity
          onPress={() => setFlash(flash === FlashMode.off ? FlashMode.on : FlashMode.off)}
          style={styles.iconBtn}
        >
          {flash === FlashMode.off
            ? <ZapOff size={22} color={Colors.textPrimary} strokeWidth={2} />
            : <Zap size={22} color={Colors.gold[500]} strokeWidth={2} />
          }
        </TouchableOpacity>
      </SafeAreaView>

      {/* Hint text */}
      <View style={styles.hintContainer}>
        <Text style={styles.hintText}>Position document within the frame</Text>
      </View>

      {/* Bottom controls */}
      <SafeAreaView edges={['bottom']} style={styles.bottomBar}>
        {/* Category selector */}
        <View style={styles.categoryRow}>
          {CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              onPress={() => setSelectedCategory(cat)}
              style={[styles.catChip, selectedCategory === cat && styles.catChipActive]}
            >
              <Text style={[styles.catText, selectedCategory === cat && styles.catTextActive]}>
                {cat}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.captureRow}>
          {pageCount > 0 && (
            <TouchableOpacity
              onPress={() => { setCapturedPhoto(null); setPageCount(0); }}
              style={styles.sideBtn}
            >
              <RotateCcw size={20} color={Colors.textPrimary} strokeWidth={2} />
            </TouchableOpacity>
          )}
          <TouchableOpacity
            onPress={handleCapture}
            disabled={isProcessing}
            style={styles.captureBtn}
          >
            <View style={[styles.captureBtnInner, isProcessing && styles.captureBtnProcessing]} />
          </TouchableOpacity>
          {pageCount > 0 && (
            <TouchableOpacity onPress={handleSave} style={[styles.sideBtn, styles.sideBtnActive]}>
              <Check size={20} color={Colors.navy[900]} strokeWidth={2.5} />
            </TouchableOpacity>
          )}
        </View>

        {isProcessing && (
          <Text style={styles.processingText}>Processing with OCR...</Text>
        )}
      </SafeAreaView>
    </View>
  );
}

const CORNER_SIZE = 24;
const CORNER_THICKNESS = 3;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  permissionContainer: {
    flex: 1, backgroundColor: Colors.background,
    alignItems: 'center', justifyContent: 'center', padding: Spacing['2xl'], gap: Spacing.base,
  },
  permissionTitle: { ...Typography.headlineSmall, color: Colors.textPrimary, textAlign: 'center' },
  permissionSub: { ...Typography.bodyMedium, color: Colors.textSecondary, textAlign: 'center', lineHeight: 24 },
  permissionBtn: {
    backgroundColor: Colors.gold[500], borderRadius: BorderRadius.full,
    paddingVertical: Spacing.base, paddingHorizontal: Spacing['2xl'], marginTop: Spacing.lg,
  },
  permissionBtnText: { ...Typography.titleSmall, color: Colors.navy[900], fontWeight: '700' },
  cancelLink: { padding: Spacing.md },
  cancelLinkText: { ...Typography.labelLarge, color: Colors.textMuted },
  overlay: {
    position: 'absolute',
    top: '25%', left: '8%', right: '8%', bottom: '25%',
  },
  cornerTL: { position: 'absolute', top: 0, left: 0, width: CORNER_SIZE, height: CORNER_SIZE, borderTopWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS, borderColor: Colors.gold[500] },
  cornerTR: { position: 'absolute', top: 0, right: 0, width: CORNER_SIZE, height: CORNER_SIZE, borderTopWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS, borderColor: Colors.gold[500] },
  cornerBL: { position: 'absolute', bottom: 0, left: 0, width: CORNER_SIZE, height: CORNER_SIZE, borderBottomWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS, borderColor: Colors.gold[500] },
  cornerBR: { position: 'absolute', bottom: 0, right: 0, width: CORNER_SIZE, height: CORNER_SIZE, borderBottomWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS, borderColor: Colors.gold[500] },
  topBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.base, paddingTop: Spacing.sm,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  iconBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.5)', alignItems: 'center', justifyContent: 'center',
  },
  topTitle: { ...Typography.titleSmall, color: Colors.textPrimary },
  hintContainer: { position: 'absolute', top: '22%', left: 0, right: 0, alignItems: 'center' },
  hintText: { ...Typography.bodySmall, color: 'rgba(255,255,255,0.7)', backgroundColor: 'rgba(0,0,0,0.4)', paddingHorizontal: Spacing.base, paddingVertical: Spacing.xs, borderRadius: BorderRadius.full },
  bottomBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    backgroundColor: 'rgba(0,0,0,0.7)', padding: Spacing.base, gap: Spacing.base,
  },
  categoryRow: { flexDirection: 'row', gap: Spacing.xs, flexWrap: 'wrap' },
  catChip: { paddingHorizontal: Spacing.sm, paddingVertical: 4, borderRadius: BorderRadius.full, backgroundColor: 'rgba(255,255,255,0.15)', borderWidth: 1, borderColor: 'transparent' },
  catChipActive: { backgroundColor: Colors.gold[500] + '30', borderColor: Colors.gold[500] },
  catText: { ...Typography.labelSmall, color: 'rgba(255,255,255,0.7)' },
  catTextActive: { color: Colors.gold[500], fontWeight: '600' },
  captureRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xl },
  captureBtn: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 3, borderColor: Colors.textPrimary,
  },
  captureBtnInner: { width: 56, height: 56, borderRadius: 28, backgroundColor: Colors.textPrimary },
  captureBtnProcessing: { backgroundColor: Colors.gold[500] },
  sideBtn: {
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center', justifyContent: 'center',
  },
  sideBtnActive: { backgroundColor: Colors.gold[500] },
  processingText: { ...Typography.bodySmall, color: Colors.gold[400], textAlign: 'center' },
});
