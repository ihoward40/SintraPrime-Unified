export type SpeechPayload = {
  text: string;
  category: string;
  threadId?: string;
  timestamp: string;
  meta?: {
    // Tier-S9
    redaction_hits?: string[];
    confidence?: number;
    severity?: "calm" | "warning" | "urgent";
    cadence?: "slow" | "normal" | "fast";
    // Tier-S12
    redaction_level?: "normal" | "strict" | "paranoid";
    // Tier-S13
    effective_voice_budget?: number;
  };
};

export interface SpeechSink {
  name: string;
  speak(payload: SpeechPayload): Promise<void> | void;
}
