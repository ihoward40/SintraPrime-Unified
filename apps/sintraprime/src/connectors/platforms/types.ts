// src/connectors/platforms/types.ts
// Unified message types and platform adapter interface for the
// Unified Message Routing Layer (UMRL).

export type Platform =
  | "telegram"
  | "whatsapp"
  | "discord"
  | "instagram"
  | "tiktok"
  | "facebook";

export interface UnifiedMessage {
  /** Unique message ID (platform-specific) */
  messageId: string;
  /** Source platform */
  platform: Platform;
  /** Platform-specific sender ID */
  senderId: string;
  /** Platform-specific chat/channel ID */
  chatId: string;
  /** Text content of the message */
  text?: string;
  /** Command (e.g., "/start", "/order") */
  command?: string;
  /** Command arguments */
  commandArgs?: string;
  /** File attachments */
  attachments?: Attachment[];
  /** Callback data from inline buttons */
  callbackData?: string;
  /** Payment information (if a payment event) */
  payment?: PaymentInfo;
  /** Raw platform-specific payload for advanced use */
  rawPayload?: any;
  /** Timestamp of the message */
  timestamp: string;
}

export interface Attachment {
  type: "document" | "image" | "video" | "audio" | "voice";
  url?: string;
  fileId?: string;
  fileName?: string;
  mimeType?: string;
  fileSize?: number;
}

export interface PaymentInfo {
  provider: string;
  chargeId: string;
  amount: number;
  currency: string;
  invoicePayload?: string;
}

export interface OutboundMessage {
  /** Target platform */
  platform: Platform;
  /** Platform-specific chat/channel ID */
  chatId: string;
  /** Text content to send */
  text?: string;
  /** File to send */
  document?: {
    url?: string;
    buffer?: Buffer;
    fileName: string;
    caption?: string;
  };
  /** Inline keyboard buttons */
  buttons?: Array<Array<{ text: string; callbackData?: string; url?: string }>>;
  /** Invoice for payment */
  invoice?: InvoiceRequest;
}

export interface InvoiceRequest {
  title: string;
  description: string;
  payload: string;
  currency: string;
  prices: Array<{ label: string; amount: number }>;
}

/**
 * Platform adapter interface — each platform implements this to
 * normalize incoming webhooks and send outbound messages.
 */
export interface PlatformAdapter {
  /** Platform identifier */
  readonly platform: Platform;

  /**
   * Parse an incoming webhook request into a UnifiedMessage.
   * Returns null if the request is not a valid message (e.g., verification challenge).
   */
  parseIncoming(headers: Record<string, string>, body: any): UnifiedMessage | null;

  /**
   * Send a message to a user on this platform.
   */
  sendMessage(message: OutboundMessage): Promise<void>;

  /**
   * Send a document/file to a user on this platform.
   */
  sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void>;

  /**
   * Send an invoice for payment on this platform (if supported).
   */
  sendInvoice?(chatId: string, invoice: InvoiceRequest): Promise<void>;
}
