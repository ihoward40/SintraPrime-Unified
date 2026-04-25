// src/connectors/platforms/index.ts
// Barrel export for all platform adapters and unified messaging types.

export type {
  Platform,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
  Attachment,
  PaymentInfo,
  PlatformAdapter,
} from "./types.js";

export { TelegramAdapter } from "./telegramAdapter.js";
export { DiscordAdapter } from "./discordAdapter.js";
export { WhatsAppAdapter } from "./whatsappAdapter.js";
export { MetaMessengerAdapter } from "./metaMessengerAdapter.js";
export { TikTokAdapter } from "./tiktokAdapter.js";
