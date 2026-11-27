/**
 * TaskDetailScreen — start a task, watch its live logs, stop it.
 *
 * Route params:
 *  - { agentId, mode: 'create' } → compose + start a new task on the agent
 *  - { taskId }                  → task detail with live log streaming
 *
 * Pattern inspiration: pingdotgg/t3code (MIT) — the phone as a remote control
 * for agents running elsewhere. Original implementation for SintraPrime.
 *
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { getRelayClient } from './relayClient';
import type {
  AgentTask,
  ControlStackParamList,
  LogEvent,
  TaskStatus,
} from './types';

type Props = NativeStackScreenProps<ControlStackParamList, 'TaskDetail'>;

const STATUS_COLORS: Record<TaskStatus, string> = {
  queued: '#8E8E93',
  running: '#007AFF',
  paused: '#FF9500',
  completed: '#34C759',
  failed: '#FF3B30',
  stopped: '#8E8E93',
};

const TERMINAL: ReadonlySet<TaskStatus> = new Set(['completed', 'failed', 'stopped']);

function isCreateParams(p: Props['route']['params']): p is { agentId: string; mode: 'create' } {
  return (p as { mode?: string }).mode === 'create';
}

function LogRow({ event }: { event: LogEvent }) {
  const color =
    event.level === 'error'
      ? '#FF3B30'
      : event.level === 'warn'
        ? '#FF9500'
        : '#1C1C1E';
  return (
    <View style={styles.logRow}>
      <Text style={styles.logSeq}>{event.seq}</Text>
      <Text style={[styles.logText, { color }]}>{event.text}</Text>
    </View>
  );
}

export default function TaskDetailScreen({ route, navigation }: Props) {
  const params = route.params;
  const createMode = isCreateParams(params);

  const [task, setTask] = useState<AgentTask | null>(null);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [loading, setLoading] = useState(!createMode);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [command, setCommand] = useState('');
  const [error, setError] = useState<string | null>(null);
  const lastSeq = useRef(0);
  const listRef = useRef<FlatList<LogEvent>>(null);

  const taskId = !createMode ? (params as { taskId: string }).taskId : null;

  const appendLogs = useCallback((events: LogEvent[]) => {
    if (events.length === 0) return;
    setLogs((prev) => {
      const seen = new Set(prev.map((e) => e.seq));
      const fresh = events.filter((e) => !seen.has(e.seq));
      if (fresh.length === 0) return prev;
      const merged = [...prev, ...fresh].sort((a, b) => a.seq - b.seq);
      lastSeq.current = Math.max(lastSeq.current, merged[merged.length - 1].seq);
      return merged;
    });
  }, []);

  // Load task + history, then stream live logs.
  useEffect(() => {
    if (createMode || !taskId) return;
    let cancelled = false;
    let unsubLogs: (() => void) | null = null;
    let unsubTask: (() => void) | null = null;

    (async () => {
      try {
        const client = await getRelayClient();
        const [t, history] = await Promise.all([
          client.getTask(taskId),
          client.getLogs(taskId, { limit: 500 }),
        ]);
        if (cancelled) return;
        setTask(t);
        appendLogs(history.logs);
        lastSeq.current = history.nextSeq - 1;

        unsubTask = client.onTaskUpdate((updated) => {
          if (!cancelled && updated.id === taskId) setTask(updated);
        });
        unsubLogs = client.subscribeLogs(taskId, (e) => {
          if (!cancelled) appendLogs([e]);
        });
        client.connect();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load task');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      unsubLogs?.();
      unsubTask?.();
    };
  }, [createMode, taskId, appendLogs]);

  // Auto-scroll to newest log line.
  useEffect(() => {
    if (logs.length > 0) {
      listRef.current?.scrollToEnd({ animated: true });
    }
  }, [logs.length]);

  const startTask = useCallback(async () => {
    if (!createMode) return;
    const agentId = (params as { agentId: string }).agentId;
    if (!title.trim()) {
      Alert.alert('Missing title', 'Give the task a short title first.');
      return;
    }
    if (!prompt.trim() && !command.trim()) {
      Alert.alert('Missing instruction', 'Provide a prompt or a command to run.');
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const client = await getRelayClient();
      const t = await client.startTask(agentId, {
        title: title.trim(),
        prompt: prompt.trim() || undefined,
        command: command.trim() || undefined,
      });
      // Swap this screen from "create" to "detail" for the new task.
      navigation.replace('TaskDetail', { taskId: t.id });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start task');
      setStarting(false);
    }
  }, [createMode, params, title, prompt, command, navigation]);

  const stopTask = useCallback(async () => {
    if (!task) return;
    setStopping(true);
    try {
      const client = await getRelayClient();
      const updated = await client.stopTask(task.id);
      setTask(updated);
    } catch (e) {
      Alert.alert('Stop failed', e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setStopping(false);
    }
  }, [task]);

  if (createMode) {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.form}>
          <Text style={styles.label}>Title</Text>
          <TextInput
            style={styles.input}
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. Nightly evidence sync"
            autoCapitalize="sentences"
          />
          <Text style={styles.label}>Prompt (natural-language instruction)</Text>
          <TextInput
            style={[styles.input, styles.multiline]}
            value={prompt}
            onChangeText={setPrompt}
            placeholder="What should the agent do?"
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />
          <Text style={styles.label}>Command (optional, alternative to prompt)</Text>
          <TextInput
            style={[styles.input, styles.mono]}
            value={command}
            onChangeText={setCommand}
            placeholder="e.g. npm run sync:evidence"
            autoCapitalize="none"
            autoCorrect={false}
          />
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <TouchableOpacity
            style={[styles.primaryButton, starting && styles.disabled]}
            onPress={startTask}
            disabled={starting}
          >
            {starting ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.primaryButtonText}>Start task</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.muted}>Loading task…</Text>
      </View>
    );
  }

  if (error && !task) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  const status = task?.status ?? 'unknown';
  const isTerminal = task ? TERMINAL.has(task.status) : true;

  return (
    <View style={styles.container}>
      <View style={styles.taskHeader}>
        <View style={styles.taskHeaderRow}>
          <View
            style={[
              styles.statusPill,
              { backgroundColor: STATUS_COLORS[task?.status ?? 'queued'] },
            ]}
          >
            <Text style={styles.statusPillText}>{status}</Text>
          </View>
          <Text style={styles.taskTitle} numberOfLines={2}>
            {task?.title}
          </Text>
        </View>
        <Text style={styles.meta}>
          {task?.id} · updated{' '}
          {task ? new Date(task.updatedAt).toLocaleString() : '—'}
          {task?.exitCode !== undefined && task.exitCode !== null
            ? ` · exit ${task.exitCode}`
            : ''}
        </Text>
        {task?.message ? <Text style={styles.meta}>{task.message}</Text> : null}
        {!isTerminal ? (
          <TouchableOpacity
            style={[styles.dangerButton, stopping && styles.disabled]}
            onPress={stopTask}
            disabled={stopping}
          >
            {stopping ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.primaryButtonText}>Stop task</Text>
            )}
          </TouchableOpacity>
        ) : null}
      </View>

      <Text style={styles.logsLabel}>Live logs</Text>
      <FlatList
        ref={listRef}
        data={logs}
        keyExtractor={(e) => String(e.seq)}
        renderItem={({ item }) => <LogRow event={item} />}
        style={styles.logList}
        contentContainerStyle={styles.logListContent}
        ListEmptyComponent={
          <Text style={styles.muted}>No log output yet.</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F2F2F7' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  muted: { color: '#8E8E93', marginTop: 4 },
  errorText: { color: '#B3261E', marginVertical: 8 },
  form: { padding: 16 },
  label: { fontSize: 14, fontWeight: '600', marginTop: 12, marginBottom: 6 },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  multiline: { minHeight: 110 },
  mono: { fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  primaryButton: {
    backgroundColor: '#007AFF',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  primaryButtonText: { color: '#FFFFFF', fontWeight: '600', fontSize: 16 },
  disabled: { opacity: 0.6 },
  taskHeader: {
    backgroundColor: '#FFFFFF',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  taskHeaderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  statusPill: { borderRadius: 12, paddingVertical: 4, paddingHorizontal: 10, marginRight: 10 },
  statusPillText: { color: '#FFFFFF', fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
  taskTitle: { fontSize: 17, fontWeight: '600', flex: 1 },
  meta: { fontSize: 13, color: '#636366', marginTop: 2 },
  dangerButton: {
    backgroundColor: '#FF3B30',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  logsLabel: {
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    color: '#8E8E93',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  logList: { flex: 1, backgroundColor: '#1C1C1E' },
  logListContent: { padding: 12, paddingBottom: 32 },
  logRow: { flexDirection: 'row', marginBottom: 4 },
  logSeq: { color: '#636366', fontSize: 12, width: 44, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  logText: { flex: 1, fontSize: 12, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
});
