// src/connectors/platforms/discordAdapter.ts
// Discord Bot API adapter for the Unified Message Routing Layer.
// Handles Discord interactions (slash commands, buttons, messages)
// and normalizes them into UnifiedMessage format.

import type {
  PlatformAdapter,
  UnifiedMessage,
  OutboundMessage,
  InvoiceRequest,
} from "./types.js";

export class DiscordAdapter implements PlatformAdapter {
  readonly platform = "discord" as const;
  private readonly botToken: string;
  private readonly apiBase = "https://discord.com/api/v10";

  constructor(config?: { botToken?: string }) {
    this.botToken = config?.botToken || process.env.DISCORD_BOT_TOKEN || "";
  }

  /**
   * Parse a Discord interaction or gateway event into a UnifiedMessage.
   */
  parseIncoming(
    headers: Record<string, string>,
    body: any
  ): UnifiedMessage | null {
    // Handle slash command interactions
    if (body.type === 2) {
      // APPLICATION_COMMAND
      const commandName = body.data?.name || "";
      const options = body.data?.options || [];
      const argsStr = options
        .map((o: any) => `${o.name}:${o.value}`)
        .join(" ");

      return {
        messageId: body.id,
        platform: "discord",
        senderId: body.member?.user?.id || body.user?.id || "",
        chatId: body.channel_id || "",
        command: `/${commandName}`,
        commandArgs: argsStr,
        timestamp: new Date().toISOString(),
        rawPayload: body,
      };
    }

    // Handle button interactions
    if (body.type === 3) {
      // MESSAGE_COMPONENT
      return {
        messageId: body.id,
        platform: "discord",
        senderId: body.member?.user?.id || body.user?.id || "",
        chatId: body.channel_id || "",
        callbackData: body.data?.custom_id,
        timestamp: new Date().toISOString(),
        rawPayload: body,
      };
    }

    // Handle regular messages (from gateway)
    if (body.content !== undefined && body.author) {
      return {
        messageId: body.id,
        platform: "discord",
        senderId: body.author.id,
        chatId: body.channel_id,
        text: body.content,
        timestamp: body.timestamp || new Date().toISOString(),
        rawPayload: body,
      };
    }

    return null;
  }

  /**
   * Send a message to a Discord channel.
   */
  async sendMessage(message: OutboundMessage): Promise<void> {
    const payload: any = {
      content: message.text || "",
    };

    if (message.buttons) {
      payload.components = [
        {
          type: 1, // ACTION_ROW
          components: message.buttons.flat().map((btn) => ({
            type: 2, // BUTTON
            style: btn.url ? 5 : 1, // LINK or PRIMARY
            label: btn.text,
            custom_id: btn.callbackData,
            url: btn.url,
          })),
        },
      ];
    }

    await this.apiCall(`/channels/${message.chatId}/messages`, "POST", payload);
  }

  /**
   * Send a document/file to a Discord channel.
   */
  async sendDocument(
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    // Discord supports file URLs in embeds or as attachments
    await this.apiCall(`/channels/${chatId}/messages`, "POST", {
      content: caption || `File: ${fileName}`,
      embeds: [
        {
          title: fileName,
          url: fileUrl,
          description: `Download: [${fileName}](${fileUrl})`,
        },
      ],
    });
  }

  /**
   * Discord doesn't have native payments — redirect to Stripe payment link.
   */
  async sendInvoice(chatId: string, invoice: InvoiceRequest): Promise<void> {
    const totalCents = invoice.prices.reduce((sum, p) => sum + p.amount, 0);
    const totalFormatted = (totalCents / 100).toFixed(2);

    await this.sendMessage({
      platform: "discord",
      chatId,
      text:
        `**${invoice.title}**\n${invoice.description}\n\n` +
        `Total: $${totalFormatted} ${invoice.currency.toUpperCase()}\n\n` +
        `Please complete payment using the link below:`,
      buttons: [
        [
          {
            text: `Pay $${totalFormatted}`,
            url: `${process.env.STRIPE_PAYMENT_LINK_BASE || "https://pay.stripe.com"}/${invoice.payload}`,
          },
        ],
      ],
    });
  }

  /**
   * Make a Discord API call.
   */
  private async apiCall(
    endpoint: string,
    method: string,
    payload?: any
  ): Promise<any> {
    const response = await fetch(`${this.apiBase}${endpoint}`, {
      method,
      headers: {
        Authorization: `Bot ${this.botToken}`,
        "Content-Type": "application/json",
      },
      body: payload ? JSON.stringify(payload) : undefined,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(
        `Discord API error: ${response.status} ${errorBody}`
      );
    }

    return response.json();
  }
}
