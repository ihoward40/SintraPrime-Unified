/**
 * Shared TypeScript types for the agent control surface.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT) — a relay server running on the
 * operator's machine plus a mobile app acting as a remote control for agents.
 * This module is an original implementation of that pattern for SintraPrime.
 *
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

/** Lifecycle state of a relay-connected agent host. */
export type AgentStatus = 'online' | 'busy' | 'offline' | 'unknown';

/** An agent host reachable through the relay server. */
export interface Agent {
  /** Stable relay-side identifier for the agent. */
  id: string;
  /** Human-readable display name. */
  name: string;
  /** Host description reported by the agent (never a secret). */
  host: string;
  /** Current reachability / workload state. */
  status: AgentStatus;
  /** ISO-8601 timestamp of the last heartbeat seen by the relay. */
  lastSeen: string;
  /** Id of the task currently running on this agent, if any. */
  currentTaskId?: string | null;
  /** Capability tags advertised by the agent (e.g. "shell", "code", "browser"). */
  capabilities?: string[];
}

/** Lifecycle state of a remote task. */
export type TaskStatus =
  | 'queued'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'stopped';

/** A unit of work executed by an agent via the relay. */
export interface AgentTask {
  id: string;
  agentId: string;
  title: string;
  /** Shell command the agent was asked to run (if command-based). */
  command?: string;
  /** Natural-language instruction given to the agent (if prompt-based). */
  prompt?: string;
  status: TaskStatus;
  /** ISO-8601 creation timestamp. */
  createdAt: string;
  /** ISO-8601 last-update timestamp. */
  updatedAt: string;
  /** Process exit code once the task reaches a terminal state. */
  exitCode?: number | null;
  /** Human-readable terminal message (error text, summary, …). */
  message?: string;
}

/** Input accepted when starting a new task. */
export interface StartTaskInput {
  title: string;
  command?: string;
  prompt?: string;
}

/** Severity of a single log line. */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/** Origin stream of a log line. */
export type LogStream = 'stdout' | 'stderr' | 'system';

/** One log event emitted by a task. */
export interface LogEvent {
  taskId: string;
  /** Monotonic per-task sequence number; used for resume/pagination. */
  seq: number;
  /** ISO-8601 timestamp assigned by the relay. */
  ts: string;
  level: LogLevel;
  stream: LogStream;
  text: string;
}

/** WebSocket connection lifecycle of the relay client. */
export type RelayConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

/** Relay server connection settings. Host is user-configured; never hardcode a real host. */
export interface RelayConfig {
  host: string;
  port: number;
  useTls: boolean;
  /** Pre-shared bearer token for the relay. Stored on-device only, never in the repo. */
  token?: string;
}

/** Navigation params for the control-surface stack. */
export type ControlStackParamList = {
  AgentList: undefined;
  TaskDetail: { taskId: string } | { agentId: string; mode: 'create' };
  RelaySettings: undefined;
};
