import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Info,
  ChevronRight,
  LogOut,
  Star,
  Moon,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import { useAuthStore } from '@store/authStore';
import { useAuth } from '@hooks/useAuth';
import { getInitials } from '@utils/formatting';

const MENU_GROUPS = [
  {
    title: 'Account',
    items: [
      { id: 'profile', label: 'Profile & Account', icon: User, screen: 'Profile' },
      { id: 'subscription', label: 'Subscription', icon: Star, color: Colors.gold[500], screen: 'Subscription' },
    ],
  },
  {
    title: 'Preferences',
    items: [
      { id: 'notifications', label: 'Notifications', icon: Bell, screen: 'Notifications' },
      { id: 'security', label: 'Security & Privacy', icon: Shield, screen: 'Security' },
    ],
  },
  {
    title: 'Support',
    items: [
      { id: 'about', label: 'About SintraPrime', icon: Info, screen: 'About' },
    ],
  },
];

export default function SettingsScreen() {
  const navigation = useNavigation<any>();
  const { user } = useAuthStore();
  const { signOut } = useAuth();

  const handleSignOut = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Sign Out', style: 'destructive', onPress: signOut },
      ],
    );
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={[Colors.navy[950], Colors.navy[900]]}
        style={styles.header}
      >
        <SafeAreaView edges={['top']}>
          <Text style={styles.headerTitle}>Settings</Text>
        </SafeAreaView>
      </LinearGradient>

      <SafeAreaView edges={['bottom']} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* User card */}
          {user && (
            <View style={styles.userCard}>
              <LinearGradient
                colors={[Colors.gold[500], Colors.gold[700]]}
                style={styles.avatar}
              >
                <Text style={styles.avatarText}>
                  {getInitials(user.firstName, user.lastName)}
                </Text>
              </LinearGradient>
              <View style={styles.userInfo}>
                <Text style={styles.userName}>{user.firstName} {user.lastName}</Text>
                <Text style={styles.userEmail}>{user.email}</Text>
                <View style={styles.tierBadge}>
                  <Star size={10} color={Colors.gold[500]} fill={Colors.gold[500]} strokeWidth={0} />
                  <Text style={styles.tierText}>{user.subscriptionTier.toUpperCase()} PLAN</Text>
                </View>
              </View>
            </View>
          )}

          {/* Menu groups */}
          {MENU_GROUPS.map((group) => (
            <View key={group.title} style={styles.group}>
              <Text style={styles.groupTitle}>{group.title}</Text>
              <View style={styles.groupCard}>
                {group.items.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <React.Fragment key={item.id}>
                      <TouchableOpacity
                        onPress={() => navigation.navigate(item.screen)}
                        style={styles.menuItem}
                        activeOpacity={0.75}
                      >
                        <View style={[styles.menuIcon, { backgroundColor: (item.color ?? Colors.textMuted) + '20' }]}>
                          <Icon size={18} color={item.color ?? Colors.textMuted} strokeWidth={1.5} />
                        </View>
                        <Text style={styles.menuLabel}>{item.label}</Text>
                        <ChevronRight size={16} color={Colors.textMuted} strokeWidth={1.5} />
                      </TouchableOpacity>
                      {i < group.items.length - 1 && <View style={styles.separator} />}
                    </React.Fragment>
                  );
                })}
              </View>
            </View>
          ))}

          {/* Sign out */}
          <TouchableOpacity onPress={handleSignOut} style={styles.signOutBtn}>
            <LogOut size={18} color={Colors.error} strokeWidth={1.5} />
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>

          <Text style={styles.version}>SintraPrime v1.0.0 · Build 1</Text>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerTitle: { ...Typography.headlineSmall, color: Colors.textPrimary, paddingTop: Spacing.base },
  scroll: { padding: Spacing.base, gap: Spacing.xl, paddingBottom: Spacing['4xl'] },
  userCard: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    backgroundColor: Colors.surface, borderRadius: BorderRadius.xl,
    padding: Spacing.base, borderWidth: 1, borderColor: Colors.border,
  },
  avatar: { width: 60, height: 60, borderRadius: 30, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 22, fontWeight: '800', color: Colors.navy[900] },
  userInfo: { flex: 1, gap: 3 },
  userName: { ...Typography.titleMedium, color: Colors.textPrimary },
  userEmail: { ...Typography.bodySmall, color: Colors.textSecondary },
  tierBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.gold[500] + '20',
    paddingHorizontal: Spacing.sm, paddingVertical: 3,
    borderRadius: BorderRadius.full, alignSelf: 'flex-start',
  },
  tierText: { ...Typography.labelSmall, color: Colors.gold[500], fontWeight: '700', fontSize: 9 },
  group: { gap: Spacing.sm },
  groupTitle: { ...Typography.labelMedium, color: Colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  groupCard: { backgroundColor: Colors.surface, borderRadius: BorderRadius.xl, borderWidth: 1, borderColor: Colors.border, overflow: 'hidden' },
  menuItem: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.md,
    padding: Spacing.base,
  },
  menuIcon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  menuLabel: { ...Typography.bodyMedium, color: Colors.textPrimary, flex: 1 },
  separator: { height: 1, backgroundColor: Colors.border, marginLeft: Spacing.base + 36 + Spacing.md },
  signOutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: Spacing.sm, padding: Spacing.base,
    borderWidth: 1, borderColor: Colors.error + '40',
    borderRadius: BorderRadius.xl,
  },
  signOutText: { ...Typography.titleSmall, color: Colors.error },
  version: { ...Typography.bodySmall, color: Colors.textMuted, textAlign: 'center' },
});
