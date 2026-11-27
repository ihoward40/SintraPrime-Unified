/**
 * AgentListScreen — roster of relay-connected agents with status.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT) — the phone as a remote control
 * for agents running elsewhere. Original implementation for SintraPrime.
 *
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { getRelayClient } from './relayClient';
import { isRelayConfigured, loadRelayConfig } from './relayConfig';
import type { Agent, AgentStatus, ControlStackParamList } from './types';

type Props = NativeStackScreenProps<ControlStackParamList, 'AgentList'>;

const STATUS_COLORS: Record<AgentStatus, string> = {
  online: '#34C759',
  busy: '#FF9500',
  offline: '#8E8E93',
  unknown: '#8E8E93',
};

function StatusDot({ status }: { status: AgentStatus }) {
  return (
    <View
      style={[
        styles.dot,
        { backgroundColor: STATUS_COLORS[status] ?? STATUS_COLORS.unknown },
      ]}
    />
  );
}

function formatLastSeen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'never';
  return d.toLocaleString();
}

export default function AgentListScreen({ navigation }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [configured, setConfigured] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const cfg = await loadRelayConfig();
      if (!isRelayConfigured(cfg)) {
        setConfigured(false);
        setAgents([]);
        return;
      }
      setConfigured(true);
      const client = await getRelayClient();
      const list = await client.listAgents();
      setAgents(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agents');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const unsub = navigation.addListener('focus', load);
    return unsub;
  }, [navigation, load]);

  // Keep the roster fresh while this screen is visible.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const client = await getRelayClient();
        const off = client.onAgentsUpdate((next) => {
          if (!cancelled) setAgents(next);
        });
        client.connect();
        return off;
      } catch {
        return undefined;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load();
  }, [load]);

  if (!configured && !loading) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Relay not configured</Text>
        <Text style={styles.muted}>
          Set your relay host and port in Settings to connect to your agents.
        </Text>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => navigation.navigate('RelaySettings')}
        >
          <Text style={styles.primaryButtonText}>Open Relay Settings</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.muted}>Contacting relay…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error ? (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => navigation.navigate('RelaySettings')}>
            <Text style={styles.errorLink}>Check settings</Text>
          </TouchableOpacity>
        </View>
      ) : null}
      <FlatList
        data={agents}
        keyExtractor={(a) => a.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.center}>
            <Text style={styles.muted}>No agents registered with the relay.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <StatusDot status={item.status} />
              <Text style={styles.agentName}>{item.name}</Text>
              <Text style={styles.statusLabel}>{item.status}</Text>
            </View>
            <Text style={styles.meta}>
              {item.host} · last seen {formatLastSeen(item.lastSeen)}
            </Text>
            {item.capabilities && item.capabilities.length > 0 ? (
              <Text style={styles.meta}>capabilities: {item.capabilities.join(', ')}</Text>
            ) : null}
            <View style={styles.actions}>
              {item.currentTaskId ? (
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => navigation.navigate('TaskDetail', { taskId: item.currentTaskId! })}
                >
                  <Text style={styles.secondaryButtonText}>View current task</Text>
                </TouchableOpacity>
              ) : null}
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={() =>
                  navigation.navigate('TaskDetail', { agentId: item.id, mode: 'create' })
                }
              >
                <Text style={styles.primaryButtonText}>Start task</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F2F2F7' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  list: { padding: 16, paddingBottom: 32 },
  title: { fontSize: 20, fontWeight: '600', marginBottom: 8 },
  muted: { color: '#8E8E93', textAlign: 'center', marginTop: 4 },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  agentName: { fontSize: 17, fontWeight: '600', flex: 1 },
  statusLabel: { fontSize: 13, color: '#8E8E93', textTransform: 'capitalize' },
  meta: { fontSize: 13, color: '#636366', marginTop: 2 },
  actions: { flexDirection: 'row', marginTop: 12, gap: 8 },
  primaryButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  primaryButtonText: { color: '#FFFFFF', fontWeight: '600', fontSize: 15 },
  secondaryButton: {
    borderColor: '#007AFF',
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  secondaryButtonText: { color: '#007AFF', fontWeight: '600', fontSize: 15 },
  errorBar: {
    backgroundColor: '#FDECEA',
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  errorText: { color: '#B3261E', flex: 1, marginRight: 8 },
  errorLink: { color: '#007AFF', fontWeight: '600' },
});
