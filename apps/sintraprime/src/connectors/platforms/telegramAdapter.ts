// src/connectors/platforms/telegramAdapter.ts
// Telegram Bot API adapter for the Unified Message Routing Layer.
// Normalizes Telegram webhook updates into UnifiedMessage format
// and provides methods for sending messages, documents, and invoices.

import type {
  PlatformAdapter,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
  Attachment,
} from "./types.js";

export class TelegramAdapter implements PlatformAdapter {
  readonly platform = "telegram" as const;
  private readonly botToken: string;
  private readonly apiBase: string;

  constructor(config?: { botToken?: string }) {
    this.botToken = config?.botToken || process.env.TELEGRAM_BOT_TOKEN || "";
    this.apiBase = `https://api.telegram.org/bot${this.botToken}`;
  }

  /**
   * Parse a Telegram webhook Update object into a UnifiedMessage.
   */
  parseIncoming(
    headers: Record<string, string>,
    body: any
  ): UnifiedMessage | null {
    // Handle regular messages
    const message = body.message || body.edited_message;
    if (message) {
      return this.parseMessage(message);
    }

    // Handle callback queries (inline button presses)
    if (body.callback_query) {
      return {
        messageId: String(body.callback_query.id),
        platform: "telegram",
        senderId: String(body.callback_query.from.id),
        chatId: String(body.callback_query.message?.chat?.id || ""),
        callbackData: body.callback_query.data,
        timestamp: new Date().toISOString(),
        rawPayload: body,
      };
    }

    // Handle successful payments
    if (body.message?.successful_payment) {
      const payment = body.message.successful_payment;
      return {
        messageId: String(body.message.message_id),
        platform: "telegram",
        senderId: String(body.message.from.id),
        chatId: String(body.message.chat.id),
        payment: {
          provider: "stripe",
          chargeId: payment.provider_payment_charge_id || "",
          amount: payment.total_amount,
          currency: payment.currency,
          invoicePayload: payment.invoice_payload,
        },
        timestamp: new Date(body.message.date * 1000).toISOString(),
        rawPayload: body,
      };
    }

    return null;
  }

  private parseMessage(message: any): UnifiedMessage {
    const text = message.text || message.caption || "";
    let command: string | undefined;
    let commandArgs: string | undefined;

    // Parse bot commands (e.g., "/start ref_123")
    if (text.startsWith("/")) {
      const parts = text.split(/\s+/);
      command = parts[0];
      commandArgs = parts.slice(1).join(" ");
    }

    // Parse attachments
    const attachments: Attachment[] = [];
    if (message.document) {
      attachments.push({
        type: "document",
        fileId: message.document.file_id,
        fileName: message.document.file_name,
        mimeType: message.document.mime_type,
        fileSize: message.document.file_size,
      });
    }
    if (message.photo) {
      const largest = message.photo[message.photo.length - 1];
      attachments.push({
        type: "image",
        fileId: largest.file_id,
        fileSize: largest.file_size,
      });
    }
    if (message.voice) {
      attachments.push({
        type: "voice",
        fileId: message.voice.file_id,
        mimeType: message.voice.mime_type,
        fileSize: message.voice.file_size,
      });
    }

    return {
      messageId: String(message.message_id),
      platform: "telegram",
      senderId: String(message.from?.id || ""),
      chatId: String(message.chat?.id || ""),
      text: text || undefined,
      command,
      commandArgs,
      attachments: attachments.length > 0 ? attachments : undefined,
      timestamp: new Date((message.date || 0) * 1000).toISOString(),
      rawPayload: message,
    };
  }

  /**
   * Send a text message with optional inline keyboard.
   */
  async sendMessage(message: OutboundMessage): Promise<void> {
    const payload: any = {
      chat_id: message.chatId,
      text: message.text || "",
      parse_mode: "Markdown",
    };

    if (message.buttons) {
      payload.reply_markup = {
        inline_keyboard: message.buttons.map((row) =>
          row.map((btn) => ({
            text: btn.text,
            callback_data: btn.callbackData,
            url: btn.url,
          }))
        ),
      };
    }

    await this.apiCall("sendMessage", payload);
  }

  /**
   * Send a document/file to a chat.
   */
  async sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    await this.apiCall("sendDocument", {
      chat_id: chatId,
      document: fileUrl,
      caption: caption || `File: ${fileName}`,
      parse_mode: "Markdown",
    });
  }

  /**
   * Send an invoice for payment via Telegram Payments API.
   */
  async sendInvoice(chatId: string, invoice: InvoiceRequest): Promise<void> {
    await this.apiCall("sendInvoice", {
      chat_id: chatId,
      title: invoice.title,
      description: invoice.description,
      payload: invoice.payload,
      provider_token: process.env.STRIPE_PROVIDER_TOKEN || "",
      currency: invoice.currency,
      prices: invoice.prices,
    });
  }

  /**
   * Answer a callback query (acknowledge inline button press).
   */
  async answerCallbackQuery(
    callbackQueryId: string,
    text?: string
  ): Promise<void> {
    await this.apiCall("answerCallbackQuery", {
      callback_query_id: callbackQueryId,
      text,
    });
  }

  /**
   * Make a Telegram Bot API call.
   */
  private async apiCall(method: string, payload: any): Promise<any> {
    const response = await fetch(`${this.apiBase}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(
        `Telegram API error (${method}): ${response.status} ${errorBody}`
      );
    }

    return response.json();
  }
}
