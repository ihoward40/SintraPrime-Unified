import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Platform, View, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
import {
  Home,
  Scale,
  TrendingUp,
  FolderOpen,
  Bot,
} from 'lucide-react-native';
import { Colors } from '@theme/colors';
import { MainTabParamList } from './types';
import HomeScreen from '@screens/dashboard/HomeScreen';
import LegalStack from './LegalStack';
import FinancialStack from './FinancialStack';
import DocumentsStack from './DocumentsStack';
import AIStack from './AIStack';

const Tab = createBottomTabNavigator<MainTabParamList>();

const TabBarBackground = () => {
  if (Platform.OS === 'ios') {
    return (
      <BlurView
        tint="dark"
        intensity={80}
        style={StyleSheet.absoluteFill}
      />
    );
  }
  return (
    <View
      style={[StyleSheet.absoluteFill, { backgroundColor: Colors.surface }]}
    />
  );
};

export default function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: Colors.gold[500],
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarStyle: {
          position: 'absolute',
          borderTopColor: Colors.border,
          borderTopWidth: 1,
          paddingBottom: Platform.OS === 'ios' ? 20 : 8,
          paddingTop: 8,
          height: Platform.OS === 'ios' ? 88 : 64,
          backgroundColor: Platform.OS === 'ios' ? 'transparent' : Colors.surface,
        },
        tabBarBackground: () => <TabBarBackground />,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ color, size }) => (
            <Home color={color} size={size} strokeWidth={1.5} />
          ),
        }}
      />
      <Tab.Screen
        name="Legal"
        component={LegalStack}
        options={{
          tabBarLabel: 'Legal',
          tabBarIcon: ({ color, size }) => (
            <Scale color={color} size={size} strokeWidth={1.5} />
          ),
        }}
      />
      <Tab.Screen
        name="Financial"
        component={FinancialStack}
        options={{
          tabBarLabel: 'Finance',
          tabBarIcon: ({ color, size }) => (
            <TrendingUp color={color} size={size} strokeWidth={1.5} />
          ),
        }}
      />
      <Tab.Screen
        name="Documents"
        component={DocumentsStack}
        options={{
          tabBarLabel: 'Vault',
          tabBarIcon: ({ color, size }) => (
            <FolderOpen color={color} size={size} strokeWidth={1.5} />
          ),
        }}
      />
      <Tab.Screen
        name="AI"
        component={AIStack}
        options={{
          tabBarLabel: 'AI Counsel',
          tabBarIcon: ({ color, size }) => (
            <Bot color={color} size={size} strokeWidth={1.5} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}
