/**
 * RelaySettingsScreen — configure the relay host/port/TLS/token.
 *
 * The relay is operator-owned infrastructure, so its address is settings, not
 * source code. Nothing entered here is committed to the repo.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT).
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RelayClient, resetRelayClient } from './relayClient';
import {
  DEFAULT_RELAY_PORT,
  isRelayConfigured,
  loadRelayConfig,
  saveRelayConfig,
} from './relayConfig';
import type { ControlStackParamList, RelayConfig } from './types';

type Props = NativeStackScreenProps<ControlStackParamList, 'RelaySettings'>;

export default function RelaySettingsScreen({ navigation }: Props) {
  const [host, setHost] = useState('');
  const [port, setPort] = useState(String(DEFAULT_RELAY_PORT));
  const [useTls, setUseTls] = useState(false);
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const cfg = await loadRelayConfig();
      setHost(cfg.host);
      setPort(String(cfg.port));
      setUseTls(cfg.useTls);
      setToken(cfg.token ?? '');
      setLoading(false);
    })();
  }, []);

  const currentConfig = (): RelayConfig => ({
    host: host.trim(),
    port: Number(port) || DEFAULT_RELAY_PORT,
    useTls,
    token: token.trim() || undefined,
  });

  const onSave = async () => {
    const cfg = currentConfig();
    if (!isRelayConfigured(cfg)) {
      Alert.alert('Missing host', 'Enter the relay host (IP or hostname).');
      return;
    }
    setSaving(true);
    try {
      await saveRelayConfig(cfg);
      resetRelayClient();
      Alert.alert('Saved', 'Relay settings saved. Reconnecting with the new settings.');
      navigation.goBack();
    } catch (e) {
      Alert.alert('Save failed', e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setSaving(false);
    }
  };

  const onTest = async () => {
    const cfg = currentConfig();
    if (!isRelayConfigured(cfg)) {
      Alert.alert('Missing host', 'Enter the relay host before testing.');
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      // Test with a throwaway client so a bad config can't poison the shared one.
      const client = new RelayClient(cfg);
      const health = await client.health();
      setTestResult(
        health.ok ? `Reachable ✓ (protocol ${'v1'})` : 'Reachable, but health check failed',
      );
    } catch (e) {
      setTestResult(`Unreachable: ${e instanceof Error ? e.message : 'unknown error'}`);
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.form}>
        <Text style={styles.hint}>
          Point the app at the relay server running on your machine. The relay
          address is never hardcoded — it lives only in these settings.
        </Text>

        <Text style={styles.label}>Host</Text>
        <TextInput
          style={[styles.input, styles.mono]}
          value={host}
          onChangeText={setHost}
          placeholder="e.g. 192.168.1.20 or relay.example.com"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <Text style={styles.label}>Port</Text>
        <TextInput
          style={[styles.input, styles.mono]}
          value={port}
          onChangeText={setPort}
          placeholder={String(DEFAULT_RELAY_PORT)}
          keyboardType="number-pad"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <View style={styles.row}>
          <Text style={styles.label}>Use TLS (https/wss)</Text>
          <Switch value={useTls} onValueChange={setUseTls} />
        </View>

        <Text style={styles.label}>Relay token (optional)</Text>
        <TextInput
          style={[styles.input, styles.mono]}
          value={token}
          onChangeText={setToken}
          placeholder="Pre-shared bearer token"
          autoCapitalize="none"
          autoCorrect={false}
          secureTextEntry
        />
        <Text style={styles.hint}>
          If your relay requires a token, paste it here. It is stored on this
          device only — never in the repo.
        </Text>

        {testResult ? <Text style={styles.testResult}>{testResult}</Text> : null}

        <TouchableOpacity
          style={[styles.secondaryButton, testing && styles.disabled]}
          onPress={onTest}
          disabled={testing}
        >
          {testing ? (
            <ActivityIndicator color="#007AFF" />
          ) : (
            <Text style={styles.secondaryButtonText}>Test connection</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.primaryButton, saving && styles.disabled]}
          onPress={onSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>Save settings</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F2F2F7' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  form: { padding: 16, paddingBottom: 40 },
  hint: { fontSize: 13, color: '#636366', marginBottom: 8 },
  label: { fontSize: 14, fontWeight: '600', marginTop: 14, marginBottom: 6 },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  mono: { fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 14,
  },
  testResult: { marginTop: 12, fontSize: 14, color: '#1C1C1E' },
  primaryButton: {
    backgroundColor: '#007AFF',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  primaryButtonText: { color: '#FFFFFF', fontWeight: '600', fontSize: 16 },
  secondaryButton: {
    borderColor: '#007AFF',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 12,
  },
  secondaryButtonText: { color: '#007AFF', fontWeight: '600', fontSize: 16 },
  disabled: { opacity: 0.6 },
});
