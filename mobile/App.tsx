import 'react-native-gesture-handler';
import './global.css';
import React, { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StyleSheet } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import * as Sentry from '@sentry/react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import RootNavigator from '@navigation/RootNavigator';
import { useAuthStore } from '@store/authStore';
import ErrorBoundary from '@components/common/ErrorBoundary';

// Keep splash visible until app is ready
SplashScreen.preventAutoHideAsync();

// Initialize Sentry for crash reporting
Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
  enableNative: true,
  tracesSampleRate: 0.2,
  environment: __DEV__ ? 'development' : 'production',
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
    },
  },
});

function AppContent() {
  const { loadStoredAuth } = useAuthStore();

  useEffect(() => {
    const init = async () => {
      try {
        await loadStoredAuth();
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        await SplashScreen.hideAsync();
      }
    };
    init();
  }, []);

  return <RootNavigator />;
}

export default Sentry.wrap(function App() {
  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={styles.root}>
        <SafeAreaProvider>
          <QueryClientProvider client={queryClient}>
            <AppContent />
          </QueryClientProvider>
        </SafeAreaProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
});

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
