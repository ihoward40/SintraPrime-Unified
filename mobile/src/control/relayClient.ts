/**
 * RelayClient — REST + WebSocket client for the agent relay server.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT) — a small relay server runs on
 * the operator's machine; the phone app is a remote control that can list
 * agents, start/stop tasks, and stream logs. This client is an original
 * implementation of that pattern for SintraPrime; the protocol is specified
 * in docs/CONTROL_SURFACE.md.
 *
 * Transport notes:
 *  - REST uses the global `fetch` (no extra dependency).
 *  - Streaming uses the global `WebSocket` available in React Native.
 *  - Auth is a pre-shared bearer token supplied via app settings
 *    (`Authorization: Bearer <token>` for REST, `?token=` for WebSocket).
 *    No token, host, or credential is hardcoded or committed to the repo.
 *
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import { loadRelayConfig } from './relayConfig';
import type {
  Agent,
  AgentTask,
  LogEvent,
  RelayConfig,
  RelayConnectionState,
  StartTaskInput,
} from './types';

/** Protocol version this client speaks. */
export const RELAY_PROTOCOL_VERSION = 'v1';

/** Server -> client WebSocket frames. */
export type ServerMessage =
  | { type: 'welcome'; protocol: string; serverTime: string }
  | { type: 'pong'; ts: string }
  | { type: 'log'; event: LogEvent }
  | { type: 'task'; task: AgentTask }
  | { type: 'agents'; agents: Agent[] }
  | { type: 'error'; message: string; code?: string };

/** Client -> server WebSocket frames. */
export type ClientMessage =
  | { type: 'ping'; ts: string }
  | { type: 'subscribe'; channel: string }
  | { type: 'unsubscribe'; channel: string };

export type LogChannel = `task:${string}:logs`;

function logChannel(taskId: string): LogChannel {
  return `task:${taskId}:logs`;
}

class RelayHttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'RelayHttpError';
    this.status = status;
  }
}

/**
 * A client bound to one relay server. Prefer `getRelayClient()` so screens
 * share a single connection; call `resetRelayClient()` after settings change.
 */
export class RelayClient {
  private config: RelayConfig;
  private ws: WebSocket | null = null;
  private state: RelayConnectionState = 'disconnected';
  private stateListeners = new Set<(s: RelayConnectionState) => void>();
  private logListeners = new Map<string, Set<(e: LogEvent) => void>>();
  private taskListeners = new Set<(t: AgentTask) => void>();
  private agentsListeners = new Set<(a: Agent[]) => void>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private intentionalClose = false;

  constructor(config: RelayConfig) {
    this.config = { ...config };
  }

  // ---------------------------------------------------------------- URLs ---

  private get scheme(): string {
    return this.config.useTls ? 'https' : 'http';
  }

  private get wsScheme(): string {
    return this.config.useTls ? 'wss' : 'ws';
  }

  /** e.g. https://relay.example:8080 */
  get baseUrl(): string {
    return `${this.scheme}://${this.config.host}:${this.config.port}`;
  }

  /** e.g. wss://relay.example:8080/ws */
  get wsUrl(): string {
    const token = this.config.token ? `?token=${encodeURIComponent(this.config.token)}` : '';
    return `${this.wsScheme}://${this.config.host}:${this.config.port}/ws${token}`;
  }

  get connectionState(): RelayConnectionState {
    return this.state;
  }

  // ------------------------------------------------------------- REST API ---

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(init.headers as Record<string, string> | undefined),
    };
    if (init.body !== undefined) headers['Content-Type'] = 'application/json';
    if (this.config.token) headers.Authorization = `Bearer ${this.config.token}`;

    const res = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    if (res.status === 204) return undefined as T;
    const text = await res.text();
    let body: unknown = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { raw: text };
    }
    if (!res.ok) {
      const msg =
        (body as { message?: string })?.message ??
        `Relay request failed (${res.status})`;
      throw new RelayHttpError(res.status, msg);
    }
    return body as T;
  }

  /** GET /v1/health — lightweight reachability check. */
  async health(): Promise<{ ok: boolean; version?: string }> {
    return this.request('/v1/health');
  }

  /** GET /v1/agents — list agents known to the relay. */
  async listAgents(): Promise<Agent[]> {
    const res = await this.request<{ agents: Agent[] }>('/v1/agents');
    return res.agents ?? [];
  }

  /** GET /v1/tasks/:taskId — fetch one task. */
  async getTask(taskId: string): Promise<AgentTask> {
    const res = await this.request<{ task: AgentTask }>(
      `/v1/tasks/${encodeURIComponent(taskId)}`,
    );
    return res.task;
  }

  /** POST /v1/tasks — start a task on an agent. */
  async startTask(agentId: string, input: StartTaskInput): Promise<AgentTask> {
    const res = await this.request<{ task: AgentTask }>('/v1/tasks', {
      method: 'POST',
      body: JSON.stringify({ agentId, ...input }),
    });
    return res.task;
  }

  /** POST /v1/tasks/:taskId/stop — request a running task to stop. */
  async stopTask(taskId: string): Promise<AgentTask> {
    const res = await this.request<{ task: AgentTask }>(
      `/v1/tasks/${encodeURIComponent(taskId)}/stop`,
      { method: 'POST' },
    );
    return res.task;
  }

  /**
   * GET /v1/tasks/:taskId/logs — fetch buffered log history.
   * Pass `after` (a seq number) to page forward from the last seen event.
   */
  async getLogs(
    taskId: string,
    opts: { after?: number; limit?: number } = {},
  ): Promise<{ logs: LogEvent[]; nextSeq: number }> {
    const q = new URLSearchParams();
    if (opts.after !== undefined) q.set('after', String(opts.after));
    if (opts.limit !== undefined) q.set('limit', String(opts.limit));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return this.request<{ logs: LogEvent[]; nextSeq: number }>(
      `/v1/tasks/${encodeURIComponent(taskId)}/logs${qs}`,
    );
  }

  // ------------------------------------------------------------ WebSocket ---

  private setState(next: RelayConnectionState): void {
    if (this.state === next) return;
    this.state = next;
    this.stateListeners.forEach((cb) => cb(next));
  }

  /** Observe connection-state transitions. Returns an unsubscribe function. */
  onConnectionState(cb: (s: RelayConnectionState) => void): () => void {
    this.stateListeners.add(cb);
    cb(this.state);
    return () => {
      this.stateListeners.delete(cb);
    };
  }

  /** Observe task lifecycle updates pushed by the relay. */
  onTaskUpdate(cb: (t: AgentTask) => void): () => void {
    this.taskListeners.add(cb);
    return () => {
      this.taskListeners.delete(cb);
    };
  }

  /** Observe agent roster updates pushed by the relay. */
  onAgentsUpdate(cb: (a: Agent[]) => void): () => void {
    this.agentsListeners.add(cb);
    return () => {
      this.agentsListeners.delete(cb);
    };
  }

  /**
   * Subscribe to live log events for one task over the shared socket.
   * The returned function unsubscribes (and closes the socket only via
   * `disconnect()` — the socket itself is shared across subscriptions).
   */
  subscribeLogs(taskId: string, cb: (e: LogEvent) => void): () => void {
    let set = this.logListeners.get(taskId);
    if (!set) {
      set = new Set();
      this.logListeners.set(taskId, set);
    }
    const first = set.size === 0;
    set.add(cb);
    if (first) this.send({ type: 'subscribe', channel: logChannel(taskId) });
    return () => {
      const s = this.logListeners.get(taskId);
      if (!s) return;
      s.delete(cb);
      if (s.size === 0) {
        this.logListeners.delete(taskId);
        this.send({ type: 'unsubscribe', channel: logChannel(taskId) });
      }
    };
  }

  /** Open the WebSocket; reconnects with backoff until `disconnect()`. */
  connect(): void {
    if (this.ws || this.state === 'connecting') return;
    if (!this.config.host) {
      this.setState('error');
      return;
    }
    this.intentionalClose = false;
    this.setState(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');
    try {
      const ws = new WebSocket(this.wsUrl);
      this.ws = ws;
      ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setState('connected');
        this.startHeartbeat();
        // Re-subscribe to channels that were active across a reconnect.
        this.logListeners.forEach((_, taskId) => {
          this.send({ type: 'subscribe', channel: logChannel(taskId) });
        });
      };
      ws.onmessage = (ev) => this.handleMessage(ev.data);
      ws.onerror = () => {
        this.setState('error');
      };
      ws.onclose = () => {
        this.ws = null;
        this.stopHeartbeat();
        if (this.intentionalClose) {
          this.setState('disconnected');
          return;
        }
        this.setState('reconnecting');
        this.scheduleReconnect();
      };
    } catch {
      this.setState('error');
      this.scheduleReconnect();
    }
  }

  /** Close the WebSocket and stop reconnect attempts. */
  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopHeartbeat();
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this.setState('disconnected');
  }

  private scheduleReconnect(): void {
    if (this.intentionalClose || this.reconnectTimer) return;
    // Exponential backoff: 1s, 2s, 4s, … capped at 30s.
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.ws = null;
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping', ts: new Date().toISOString() });
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private send(msg: ClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private handleMessage(data: unknown): void {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(String(data)) as ServerMessage;
    } catch {
      return;
    }
    switch (msg.type) {
      case 'log':
        this.logListeners.get(msg.event.taskId)?.forEach((cb) => cb(msg.event));
        break;
      case 'task':
        this.taskListeners.forEach((cb) => cb(msg.task));
        break;
      case 'agents':
        this.agentsListeners.forEach((cb) => cb(msg.agents));
        break;
      case 'error':
        // Surface relay-side errors through the connection state channel
        // only when there is no usable connection; otherwise ignore.
        break;
      default:
        break;
    }
  }
}

// ------------------------------------------------------- shared instance ---

let shared: RelayClient | null = null;

/**
 * Shared client built from the saved relay settings. Screens should use this
 * so the app holds a single WebSocket connection.
 */
export async function getRelayClient(): Promise<RelayClient> {
  if (!shared) {
    shared = new RelayClient(await loadRelayConfig());
  }
  return shared;
}

/** Drop the shared client (e.g. after the user changes relay settings). */
export function resetRelayClient(): void {
  if (shared) {
    shared.disconnect();
    shared = null;
  }
}
