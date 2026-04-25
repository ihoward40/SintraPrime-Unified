// src/connectors/platforms/metaMessengerAdapter.ts
// Unified adapter for Facebook Messenger and Instagram Messaging APIs.
// Both platforms use the Meta Send API with similar payloads,
// differing primarily in the page token and webhook structure.

import type {
  PlatformAdapter,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
  Platform,
} from "./types.js";

export class MetaMessengerAdapter implements PlatformAdapter {
  readonly platform: Platform;
  private readonly pageAccessToken: string;
  private readonly apiBase: string;

  constructor(config: {
    platform: "facebook" | "instagram";
    pageAccessToken?: string;
    apiVersion?: string;
  }) {
    this.platform = config.platform;
    const apiVersion = config.apiVersion || "v18.0";

    if (config.platform === "facebook") {
      this.pageAccessToken =
        config.pageAccessToken || process.env.FACEBOOK_PAGE_ACCESS_TOKEN || "";
    } else {
      this.pageAccessToken =
        config.pageAccessToken || process.env.INSTAGRAM_ACCESS_TOKEN || "";
    }

    this.apiBase = `https://graph.facebook.com/${apiVersion}/me`;
  }

  /**
   * Parse a Meta webhook event into a UnifiedMessage.
   * Works for both Facebook Messenger and Instagram messaging webhooks.
   */
  parseIncoming(
    headers: Record<string, string>,
    body: any
  ): UnifiedMessage | null {
    const entry = body.entry?.[0];
    if (!entry) return null;

    // Facebook Messenger uses "messaging", Instagram uses "messaging" too
    const messagingEvent = entry.messaging?.[0];
    if (!messagingEvent) return null;

    const senderId = messagingEvent.sender?.id;
    if (!senderId) return null;

    // Handle regular messages
    if (messagingEvent.message) {
      const msg = messagingEvent.message;
      const unified: UnifiedMessage = {
        messageId: msg.mid || `${Date.now()}`,
        platform: this.platform,
        senderId,
        chatId: senderId, // Meta uses sender ID as chat ID for 1:1
        text: msg.text,
        timestamp: new Date(messagingEvent.timestamp).toISOString(),
        rawPayload: body,
      };

      // Parse quick reply payloads
      if (msg.quick_reply?.payload) {
        unified.callbackData = msg.quick_reply.payload;
      }

      // Parse attachments
      if (msg.attachments) {
        unified.attachments = msg.attachments.map((att: any) => ({
          type: att.type === "file" ? "document" : att.type,
          url: att.payload?.url,
        }));
      }

      // Parse commands from text
      if (unified.text?.startsWith("/")) {
        const parts = unified.text.split(/\s+/);
        unified.command = parts[0];
        unified.commandArgs = parts.slice(1).join(" ");
      }

      return unified;
    }

    // Handle postback (button clicks)
    if (messagingEvent.postback) {
      return {
        messageId: `postback-${Date.now()}`,
        platform: this.platform,
        senderId,
        chatId: senderId,
        callbackData: messagingEvent.postback.payload,
        text: messagingEvent.postback.title,
        timestamp: new Date(messagingEvent.timestamp).toISOString(),
        rawPayload: body,
      };
    }

    return null;
  }

  /**
   * Send a message via Meta Send API.
   */
  async sendMessage(message: OutboundMessage): Promise<void> {
    const payload: any = {
      recipient: { id: message.chatId },
      message: {} as any,
    };

    if (message.buttons && message.buttons.length > 0) {
      // Use button template (max 3 buttons for Messenger)
      const flatButtons = message.buttons.flat().slice(0, 3);
      payload.message = {
        attachment: {
          type: "template",
          payload: {
            template_type: "button",
            text: message.text || "Choose an option:",
            buttons: flatButtons.map((btn) => {
              if (btn.url) {
                return { type: "web_url", url: btn.url, title: btn.text };
              }
              return { type: "postback", title: btn.text, payload: btn.callbackData || btn.text };
            }),
          },
        },
      };
    } else {
      payload.message = { text: message.text || "" };
    }

    await this.apiCall("/messages", payload);
  }

  /**
   * Send a document via Meta Send API.
   */
  async sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    await this.apiCall("/messages", {
      recipient: { id: chatId },
      message: {
        attachment: {
          type: "file",
          payload: { url: fileUrl, is_reusable: true },
        },
      },
    });

    // Send caption as a follow-up text message
    if (caption) {
      await this.apiCall("/messages", {
        recipient: { id: chatId },
        message: { text: caption },
      });
    }
  }

  /**
   * Meta platforms don't have native payments — send a Stripe payment link.
   */
  async sendInvoice(chatId: string, invoice: InvoiceRequest): Promise<void> {
    const totalCents = invoice.prices.reduce((sum, p) => sum + p.amount, 0);
    const totalFormatted = (totalCents / 100).toFixed(2);
    const paymentUrl = `${process.env.STRIPE_PAYMENT_LINK_BASE || "https://pay.stripe.com"}/${invoice.payload}`;

    await this.sendMessage({
      platform: this.platform,
      chatId,
      text: `${invoice.title}\n${invoice.description}\nTotal: $${totalFormatted}`,
      buttons: [[{ text: `Pay $${totalFormatted}`, url: paymentUrl }]],
    });
  }

  /**
   * Make a Meta Graph API call.
   */
  private async apiCall(endpoint: string, payload: any): Promise<any> {
    const url = `${this.apiBase}${endpoint}?access_token=${this.pageAccessToken}`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Meta API error (${this.platform}): ${response.status} ${errorBody}`);
    }

    return response.json();
  }
}
