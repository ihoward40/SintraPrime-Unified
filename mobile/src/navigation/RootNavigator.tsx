import React, { useEffect } from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { Colors } from '@theme/colors';
import { useAuthStore } from '@store/authStore';
import { RootStackParamList } from './types';
import MainTabs from './MainTabs';
import AuthStack from './AuthStack';

const Stack = createNativeStackNavigator<RootStackParamList>();

const NavTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    primary: Colors.gold[500],
    background: Colors.background,
    card: Colors.surface,
    text: Colors.textPrimary,
    border: Colors.border,
    notification: Colors.gold[500],
  },
};

const linking = {
  prefixes: ['sintraprime://', 'https://app.sintraprime.com'],
  config: {
    screens: {
      Main: {
        screens: {
          Home: 'home',
          Legal: {
            screens: {
              LegalHub: 'legal',
              CaseDetail: 'legal/case/:caseId',
              CaseLawSearch: 'legal/search',
            },
          },
          Financial: {
            screens: {
              Financial: 'financial',
              CreditScore: 'financial/credit',
            },
          },
          AI: {
            screens: {
              AIAssistant: 'ai',
            },
          },
        },
      },
    },
  },
};

export default function RootNavigator() {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) return null;

  return (
    <NavigationContainer theme={NavTheme} linking={linking}>
      <StatusBar style="light" />
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <Stack.Screen name="Main" component={MainTabs} />
        ) : (
          <Stack.Screen name="Auth" component={AuthStack} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
