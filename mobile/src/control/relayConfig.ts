/**
 * Relay connection settings: load / save / defaults.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT) — relay host is operator-owned
 * infrastructure, so the mobile app must treat the host as configuration, not
 * as a constant. No real host is ever hardcoded here.
 *
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import type { RelayConfig } from './types';

const STORAGE_KEY = 'control.relay.config.v1';

/** Port the reference relay server listens on. Change in Settings if yours differs. */
export const DEFAULT_RELAY_PORT = 8080;

/** Safe placeholder — the user must set a real host in Settings before connecting. */
export const DEFAULT_RELAY_HOST = '';

const DEFAULTS: RelayConfig = {
  host: DEFAULT_RELAY_HOST,
  port: DEFAULT_RELAY_PORT,
  useTls: false,
  token: undefined,
};

type KVStore = {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
};

/**
 * Best-effort persistent storage. Uses AsyncStorage when the host app has it
 * installed; otherwise falls back to in-memory storage for the session.
 */
function resolveStore(): KVStore {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires, global-require
    const mod = require('@react-native-async-storage/async-storage');
    const store = mod?.default ?? mod;
    if (store && typeof store.getItem === 'function') {
      return store as KVStore;
    }
  } catch {
    // AsyncStorage not installed — session-only storage.
  }
  const mem = new Map<string, string>();
  return {
    getItem: async (k) => (mem.has(k) ? mem.get(k)! : null),
    setItem: async (k, v) => {
      mem.set(k, v);
    },
  };
}

const store = resolveStore();

function sanitize(raw: Partial<RelayConfig>): RelayConfig {
  const port = Number(raw.port);
  return {
    host: (raw.host ?? DEFAULTS.host).trim(),
    port: Number.isFinite(port) && port > 0 && port <= 65535 ? port : DEFAULTS.port,
    useTls: Boolean(raw.useTls),
    token: raw.token && raw.token.trim() ? raw.token.trim() : undefined,
  };
}

/** Load the saved relay config, or defaults when nothing was saved yet. */
export async function loadRelayConfig(): Promise<RelayConfig> {
  try {
    const raw = await store.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };
    return sanitize(JSON.parse(raw) as Partial<RelayConfig>);
  } catch {
    return { ...DEFAULTS };
  }
}

/** Persist the relay config on-device. Never commit a real host/token to the repo. */
export async function saveRelayConfig(config: RelayConfig): Promise<void> {
  await store.setItem(STORAGE_KEY, JSON.stringify(sanitize(config)));
}

/** True when the config has a host the client can actually dial. */
export function isRelayConfigured(config: RelayConfig): boolean {
  return config.host.length > 0;
}
