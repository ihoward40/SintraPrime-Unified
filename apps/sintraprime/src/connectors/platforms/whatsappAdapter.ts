// src/connectors/platforms/whatsappAdapter.ts
// WhatsApp Cloud API adapter for the Unified Message Routing Layer.
// Normalizes WhatsApp webhook events into UnifiedMessage format
// and provides methods for sending messages via the Cloud API.

import type {
  PlatformAdapter,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
} from "./types.js";

export class WhatsAppAdapter implements PlatformAdapter {
  readonly platform = "whatsapp" as const;
  private readonly accessToken: string;
  private readonly phoneNumberId: string;
  private readonly apiBase: string;

  constructor(config?: { accessToken?: string; phoneNumberId?: string; apiVersion?: string }) {
    this.accessToken = config?.accessToken || process.env.WHATSAPP_ACCESS_TOKEN || "";
    this.phoneNumberId = config?.phoneNumberId || process.env.WHATSAPP_PHONE_NUMBER_ID || "";
    const apiVersion = config?.apiVersion || "v18.0";
    this.apiBase = `https://graph.facebook.com/${apiVersion}/${this.phoneNumberId}`;
  }

  /**
   * Parse a WhatsApp Cloud API webhook payload into a UnifiedMessage.
   */
  parseIncoming(
    headers: Record<string, string>,
    body: any
  ): UnifiedMessage | null {
    // WhatsApp webhooks have a nested structure
    const entry = body.entry?.[0];
    const changes = entry?.changes?.[0];
    const value = changes?.value;

    if (!value?.messages?.[0]) return null;

    const msg = value.messages[0];
    const contact = value.contacts?.[0];

    const unified: UnifiedMessage = {
      messageId: msg.id,
      platform: "whatsapp",
      senderId: msg.from,
      chatId: msg.from, // WhatsApp uses phone number as chat ID
      timestamp: new Date(parseInt(msg.timestamp) * 1000).toISOString(),
      rawPayload: body,
    };

    switch (msg.type) {
      case "text":
        unified.text = msg.text?.body;
        // Parse commands from text (e.g., "!start" or "/start")
        if (unified.text?.startsWith("/") || unified.text?.startsWith("!")) {
          const parts = unified.text.split(/\s+/);
          unified.command = (parts[0] ?? "").replace("!", "/");
          unified.commandArgs = parts.slice(1).join(" ");
        }
        break;
      case "document":
        unified.attachments = [{
          type: "document",
          fileId: msg.document?.id,
          fileName: msg.document?.filename,
          mimeType: msg.document?.mime_type,
        }];
        unified.text = msg.document?.caption;
        break;
      case "image":
        unified.attachments = [{
          type: "image",
          fileId: msg.image?.id,
          mimeType: msg.image?.mime_type,
        }];
        unified.text = msg.image?.caption;
        break;
      case "interactive":
        // Button replies or list selections
        if (msg.interactive?.type === "button_reply") {
          unified.callbackData = msg.interactive.button_reply?.id;
          unified.text = msg.interactive.button_reply?.title;
        } else if (msg.interactive?.type === "list_reply") {
          unified.callbackData = msg.interactive.list_reply?.id;
          unified.text = msg.interactive.list_reply?.title;
        }
        break;
    }

    return unified;
  }

  /**
   * Send a text message with optional buttons via WhatsApp Cloud API.
   */
  async sendMessage(message: OutboundMessage): Promise<void> {
    if (message.buttons && message.buttons.length > 0) {
      // Use interactive message with buttons (max 3 buttons)
      const flatButtons = message.buttons.flat().slice(0, 3);
      await this.apiCall("/messages", {
        messaging_product: "whatsapp",
        to: message.chatId,
        type: "interactive",
        interactive: {
          type: "button",
          body: { text: message.text || "" },
          action: {
            buttons: flatButtons.map((btn, i) => ({
              type: "reply",
              reply: {
                id: btn.callbackData || `btn_${i}`,
                title: btn.text.substring(0, 20), // WhatsApp limits to 20 chars
              },
            })),
          },
        },
      });
    } else {
      // Simple text message
      await this.apiCall("/messages", {
        messaging_product: "whatsapp",
        to: message.chatId,
        type: "text",
        text: { body: message.text || "" },
      });
    }
  }

  /**
   * Send a document via WhatsApp Cloud API.
   */
  async sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    await this.apiCall("/messages", {
      messaging_product: "whatsapp",
      to: chatId,
      type: "document",
      document: {
        link: fileUrl,
        filename: fileName,
        caption: caption || `File: ${fileName}`,
      },
    });
  }

  /**
   * WhatsApp doesn't have native payments — send a payment link message.
   */
  async sendInvoice(chatId: string, invoice: InvoiceRequest): Promise<void> {
    const totalCents = invoice.prices.reduce((sum, p) => sum + p.amount, 0);
    const totalFormatted = (totalCents / 100).toFixed(2);
    const paymentUrl = `${process.env.STRIPE_PAYMENT_LINK_BASE || "https://pay.stripe.com"}/${invoice.payload}`;

    await this.sendMessage({
      platform: "whatsapp",
      chatId,
      text:
        `*${invoice.title}*\n${invoice.description}\n\n` +
        `Total: $${totalFormatted} ${invoice.currency.toUpperCase()}\n\n` +
        `Complete your payment here: ${paymentUrl}`,
    });
  }

  /**
   * Make a WhatsApp Cloud API call.
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
      throw new Error(`WhatsApp API error: ${response.status} ${errorBody}`);
    }

    return response.json();
  }
}
