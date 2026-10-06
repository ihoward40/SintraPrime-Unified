/**
 * Public surface of the agent control module.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT).
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

export { RelayClient, getRelayClient, resetRelayClient, RELAY_PROTOCOL_VERSION } from './relayClient';
export type { ServerMessage, ClientMessage, LogChannel } from './relayClient';
export {
  loadRelayConfig,
  saveRelayConfig,
  isRelayConfigured,
  DEFAULT_RELAY_PORT,
  DEFAULT_RELAY_HOST,
} from './relayConfig';
export type {
  Agent,
  AgentStatus,
  AgentTask,
  TaskStatus,
  StartTaskInput,
  LogEvent,
  LogLevel,
  LogStream,
  RelayConfig,
  RelayConnectionState,
  ControlStackParamList,
} from './types';
export { default as AgentListScreen } from './AgentListScreen';
export { default as TaskDetailScreen } from './TaskDetailScreen';
export { default as RelaySettingsScreen } from './RelaySettingsScreen';
