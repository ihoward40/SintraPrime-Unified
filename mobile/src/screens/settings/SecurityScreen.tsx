import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Fingerprint, Shield, Clock, Eye, Lock, Trash2 } from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import GradientHeader from '@components/common/GradientHeader';
import { useAuthStore } from '@store/authStore';
import { useBiometric } from '@hooks/useBiometric';

export default function SecurityScreen() {
  const { user, biometricEnabled, enableBiometric, disableBiometric } = useAuthStore();
  const biometric = useBiometric();
  const [autoLock, setAutoLock] = useState(true);
  const [screenshotPrevention, setScreenshotPrevention] = useState(true);
  const [biometricAvail, setBiometricAvail] = useState(false);

  useEffect(() => {
    biometric.checkAvailability().then((state) => {
      setBiometricAvail(state.isAvailable && state.isEnrolled);
    });
  }, []);

  const handleBiometricToggle = async (value: boolean) => {
    if (value) {
      const success = await biometric.authenticate('Enable biometric login');
      if (success) {
        enableBiometric();
      } else {
        Alert.alert('Authentication Failed', 'Could not enable biometric login.');
      }
    } else {
      disableBiometric();
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      <GradientHeader title="Security & Privacy" showBack />
      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Authentication</Text>
            <View style={styles.card}>
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <View style={[styles.icon, { backgroundColor: Colors.gold[500] + '20' }]}>
                    <Fingerprint size={18} color={Colors.gold[500]} strokeWidth={1.5} />
                  </View>
                  <View>
                    <Text style={styles.rowTitle}>Biometric Login</Text>
                    <Text style={styles.rowSub}>Face ID / Touch ID</Text>
                  </View>
                </View>
                <Switch
                  value={biometricEnabled}
                  onValueChange={handleBiometricToggle}
                  disabled={!biometricAvail}
                  trackColor={{ false: Colors.border, true: Colors.gold[500] }}
                  thumbColor={Colors.textPrimary}
                />
              </View>
              <View style={styles.separator} />
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <View style={[styles.icon, { backgroundColor: Colors.info + '20' }]}>
                    <Clock size={18} color={Colors.info} strokeWidth={1.5} />
                  </View>
                  <View>
                    <Text style={styles.rowTitle}>Auto-Lock</Text>
                    <Text style={styles.rowSub}>Lock after 5 min background</Text>
                  </View>
                </View>
                <Switch
                  value={autoLock}
                  onValueChange={setAutoLock}
                  trackColor={{ false: Colors.border, true: Colors.gold[500] }}
                  thumbColor={Colors.textPrimary}
                />
              </View>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Privacy</Text>
            <View style={styles.card}>
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <View style={[styles.icon, { backgroundColor: Colors.warning + '20' }]}>
                    <Eye size={18} color={Colors.warning} strokeWidth={1.5} />
                  </View>
                  <View>
                    <Text style={styles.rowTitle}>Screenshot Prevention</Text>
                    <Text style={styles.rowSub}>Block screenshots in the app</Text>
                  </View>
                </View>
                <Switch
                  value={screenshotPrevention}
                  onValueChange={setScreenshotPrevention}
                  trackColor={{ false: Colors.border, true: Colors.gold[500] }}
                  thumbColor={Colors.textPrimary}
                />
              </View>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Danger Zone</Text>
            <TouchableOpacity
              style={styles.dangerBtn}
              onPress={() =>
                Alert.alert('Delete Account', 'This will permanently delete your account and all data. This cannot be undone.', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Delete', style: 'destructive' },
                ])
              }
            >
              <Trash2 size={18} color={Colors.error} strokeWidth={1.5} />
              <Text style={styles.dangerText}>Delete Account & Data</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: Spacing.base, gap: Spacing.xl, paddingBottom: Spacing['3xl'] },
  section: { gap: Spacing.sm },
  sectionTitle: { ...Typography.labelMedium, color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  card: { backgroundColor: Colors.surface, borderRadius: BorderRadius.xl, borderWidth: 1, borderColor: Colors.border, overflow: 'hidden' },
  row: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: Spacing.base,
  },
  rowLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, flex: 1 },
  icon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  rowTitle: { ...Typography.bodyMedium, color: Colors.textPrimary },
  rowSub: { ...Typography.bodySmall, color: Colors.textMuted },
  separator: { height: 1, backgroundColor: Colors.border, marginLeft: 16 + 36 + 16 },
  dangerBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, padding: Spacing.base,
    borderWidth: 1, borderColor: Colors.error + '40',
    borderRadius: BorderRadius.xl,
  },
  dangerText: { ...Typography.titleSmall, color: Colors.error },
});
