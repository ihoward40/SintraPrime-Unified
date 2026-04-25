// src/connectors/platforms/tiktokAdapter.ts
// TikTok Business API adapter for the Unified Message Routing Layer.
// Handles TikTok comment-to-DM conversion and direct messaging.
// TikTok has strict 24-hour reply windows and automation rules.

import type {
  PlatformAdapter,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
} from "./types.js";

export class TikTokAdapter implements PlatformAdapter {
  readonly platform = "tiktok" as const;
  private readonly accessToken: string;
  private readonly apiBase = "https://open.tiktokapis.com/v2";

  constructor(config?: { accessToken?: string }) {
    this.accessToken = config?.accessToken || process.env.TIKTOK_ACCESS_TOKEN || "";
  }

  /**
   * Parse a TikTok webhook event into a UnifiedMessage.
   * TikTok webhooks can deliver comment events or DM events.
   */
  parseIncoming(
    headers: Record<string, string>,
    body: any
  ): UnifiedMessage | null {
    // Handle DM (direct message) events
    if (body.event === "receive_message" && body.content) {
      return {
        messageId: body.msg_id || `tiktok-${Date.now()}`,
        platform: "tiktok",
        senderId: body.from_user_id || body.sender?.open_id || "",
        chatId: body.conversation_id || body.from_user_id || "",
        text: body.content?.text,
        timestamp: body.create_time
          ? new Date(body.create_time * 1000).toISOString()
          : new Date().toISOString(),
        rawPayload: body,
      };
    }

    // Handle comment events (for comment-to-DM conversion)
    if (body.event === "comment" || body.type === "comment") {
      const comment = body.content || body.comment || {};
      return {
        messageId: comment.comment_id || `tiktok-comment-${Date.now()}`,
        platform: "tiktok",
        senderId: comment.user_id || body.user?.open_id || "",
        chatId: comment.user_id || "", // Will need to initiate DM
        text: comment.text || comment.comment_text,
        timestamp: new Date().toISOString(),
        rawPayload: body,
      };
    }

    return null;
  }

  /**
   * Send a DM via TikTok API.
   * Note: TikTok has strict limitations on automated messaging.
   */
  async sendMessage(message: OutboundMessage): Promise<void> {
    await this.apiCall("/dm/message/send/", {
      conversation_id: message.chatId,
      content: {
        text: message.text || "",
      },
    });
  }

  /**
   * Send a document link via TikTok DM.
   * TikTok DMs don't support direct file uploads — send a download link.
   */
  async sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    await this.sendMessage({
      platform: "tiktok",
      chatId,
      text: `${caption || "Your file is ready!"}\n\nDownload: ${fileUrl}`,
    });
  }

  /**
   * TikTok doesn't have native payments — send a Stripe payment link.
   */
  async sendInvoice(chatId: string, invoice: InvoiceRequest): Promise<void> {
    const totalCents = invoice.prices.reduce((sum, p) => sum + p.amount, 0);
    const totalFormatted = (totalCents / 100).toFixed(2);
    const paymentUrl = `${process.env.STRIPE_PAYMENT_LINK_BASE || "https://pay.stripe.com"}/${invoice.payload}`;

    await this.sendMessage({
      platform: "tiktok",
      chatId,
      text:
        `${invoice.title}\n${invoice.description}\n\n` +
        `Total: $${totalFormatted} ${invoice.currency.toUpperCase()}\n\n` +
        `Pay here: ${paymentUrl}`,
    });
  }

  /**
   * Make a TikTok API call.
   */
  private async apiCall(endpoint: string, payload: any): Promise<any> {
    const response = await fetch(`${this.apiBase}${endpoint}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`TikTok API error: ${response.status} ${errorBody}`);
    }

    return response.json();
  }
}
