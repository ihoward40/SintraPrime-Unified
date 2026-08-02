import { apiClient } from './client';

/**
 * SP-VOICE-001 Increment Two client — governed voice command ledger.
 *
 * Every command this API can produce is a mock/sandboxed provider outcome
 * (see `voice/governed/mock_providers.py` and
 * `portal/services/voice_command_service.py`). This client never places a
 * real phone call, sends a real email/message, creates a real calendar
 * event, submits a real filing, or moves real money — it only reads and
 * drives the governed mock ledger.
 */

export type VoiceSource = 'desktop_voice' | 'mobile_voice' | 'telephony' | 'text_fallback';

export interface VoiceCommandResponse {
  command_id: string;
  voice_session_id: string;
  correlation_id: string;
  source: string;
  normalized_intent: string;
  resolved_capability: string;
  target_resource: string | null;
  risk_class: string;
  policy_decision: string;
  confirmation_state: string;
  session_state: string;
  result: string;
  reason: string | null;
  provider_capability: string | null;
  provider_resource_id: string | null;
  provider_mock: boolean | null;
  artifacts: unknown[];
  audit_log_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface VoiceCommandSubmitRequest {
  raw_transcript: string;
  source?: VoiceSource;
  voice_session_id?: string;
  requested_capability?: string;
  target_resource?: string;
  normalized_intent?: string;
}

export interface VoiceCommandConfirmRequest {
  utterance: string;
  current_target?: string;
}

export interface VoiceCommandCancelRequest {
  reason?: string;
}

export const voiceApi = {
  /** Submit a new voice command for classification, policy evaluation, and (if allowed) mock execution. */
  submit: (body: VoiceCommandSubmitRequest) =>
    apiClient.post<VoiceCommandResponse>('/voice/commands', body).then((r) => r.data),

  /** Get a single voice command by its `vcmd-...` id. */
  get: (commandId: string) =>
    apiClient.get<VoiceCommandResponse>(`/voice/commands/${commandId}`).then((r) => r.data),

  /** List voice commands for the caller's tenant, optionally scoped to one voice session. */
  list: (voiceSessionId?: string) =>
    apiClient
      .get<VoiceCommandResponse[]>('/voice/commands', {
        params: voiceSessionId ? { voice_session_id: voiceSessionId } : undefined,
      })
      .then((r) => r.data),

  /** Confirm (or deny) a command awaiting confirmation. */
  confirm: (commandId: string, body: VoiceCommandConfirmRequest) =>
    apiClient.post<VoiceCommandResponse>(`/voice/commands/${commandId}/confirm`, body).then((r) => r.data),

  /** Cancel an in-flight (non-terminal) voice command. */
  cancel: (commandId: string, body: VoiceCommandCancelRequest = {}) =>
    apiClient.post<VoiceCommandResponse>(`/voice/commands/${commandId}/cancel`, body).then((r) => r.data),
};

export default voiceApi;
