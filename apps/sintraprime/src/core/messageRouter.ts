// src/core/messageRouter.ts
// Unified Message Routing Layer (UMRL) — the central message routing engine.
// Receives normalized UnifiedMessages from any platform adapter, routes them
// through SintraPrime's governance pipeline, and dispatches responses back
// through the correct platform adapter.

import type {
  Platform,
  UnifiedMessage,
  OutboundMessage,
  PlatformAdapter,
} from "../connectors/platforms/types.js";

export interface UserSession {
  userId: string;
  platform: Platform;
  chatId: string;
  subscriptionTier: "free" | "pro" | "enterprise";
  conversationState: string;
  lastActivity: string;
  context: Record<string, any>;
}

export interface RouteResult {
  handled: boolean;
  response?: OutboundMessage;
  taskId?: string;
  error?: string;
}

export type MessageHandler = (
  message: UnifiedMessage,
  session: UserSession
) => Promise<RouteResult>;

/**
 * MessageRouter is the core of the Unified Message Routing Layer.
 * It manages platform adapters, user sessions, and message routing.
 */
export class MessageRouter {
  private adapters: Map<Platform, PlatformAdapter> = new Map();
  private sessions: Map<string, UserSession> = new Map();
  private commandHandlers: Map<string, MessageHandler> = new Map();
  private callbackHandlers: Map<string, MessageHandler> = new Map();
  private defaultHandler: MessageHandler | null = null;

  /**
   * Register a platform adapter.
   */
  registerAdapter(adapter: PlatformAdapter): void {
    this.adapters.set(adapter.platform, adapter);
    console.log(`[MessageRouter] Registered adapter: ${adapter.platform}`);
  }

  /**
   * Register a command handler (e.g., "/start", "/order").
   */
  onCommand(command: string, handler: MessageHandler): void {
    this.commandHandlers.set(command.toLowerCase(), handler);
  }

  /**
   * Register a callback data handler (for inline button presses).
   */
  onCallback(prefix: string, handler: MessageHandler): void {
    this.callbackHandlers.set(prefix, handler);
  }

  /**
   * Register a default handler for unmatched messages.
   */
  onDefault(handler: MessageHandler): void {
    this.defaultHandler = handler;
  }

  /**
   * Get or create a user session.
   */
  getSession(platform: Platform, senderId: string, chatId: string): UserSession {
    const sessionKey = `${platform}:${senderId}`;
    let session = this.sessions.get(sessionKey);

    if (!session) {
      session = {
        userId: senderId,
        platform,
        chatId,
        subscriptionTier: "free",
        conversationState: "idle",
        lastActivity: new Date().toISOString(),
        context: {},
      };
      this.sessions.set(sessionKey, session);
    }

    session.lastActivity = new Date().toISOString();
    return session;
  }

  /**
   * Process an incoming webhook from any platform.
   * This is the main entry point called by the airlock server.
   */
  async processIncoming(
    platform: Platform,
    headers: Record<string, string>,
    body: any
  ): Promise<RouteResult> {
    const adapter = this.adapters.get(platform);
    if (!adapter) {
      return { handled: false, error: `No adapter registered for platform: ${platform}` };
    }

    // Parse the incoming webhook into a UnifiedMessage
    const message = adapter.parseIncoming(headers, body);
    if (!message) {
      return { handled: false, error: "Could not parse incoming message" };
    }

    // Get or create user session
    const session = this.getSession(message.platform, message.senderId, message.chatId);

    // Route the message
    let result: RouteResult;

    // 1. Check for command handlers
    if (message.command) {
      const handler = this.commandHandlers.get(message.command.toLowerCase());
      if (handler) {
        result = await handler(message, session);
      } else {
        result = {
          handled: true,
          response: {
            platform: message.platform,
            chatId: message.chatId,
            text: `Unknown command: ${message.command}. Type /help for available commands.`,
          },
        };
      }
    }
    // 2. Check for callback handlers
    else if (message.callbackData) {
      const prefix = message.callbackData.split(":")[0] ?? "";
      const handler = this.callbackHandlers.get(prefix);
      if (handler) {
        result = await handler(message, session);
      } else {
        result = { handled: false, error: `No handler for callback: ${prefix}` };
      }
    }
    // 3. Check for payment events
    else if (message.payment) {
      const handler = this.callbackHandlers.get("payment");
      if (handler) {
        result = await handler(message, session);
      } else {
        result = { handled: false, error: "No payment handler registered" };
      }
    }
    // 4. Fall through to default handler
    else if (this.defaultHandler) {
      result = await this.defaultHandler(message, session);
    } else {
      result = { handled: false, error: "No handler matched" };
    }

    // Send the response back through the platform adapter
    if (result.response) {
      await adapter.sendMessage(result.response);
    }

    return result;
  }

  /**
   * Send a proactive message to a user on any platform.
   * Used for delivery notifications, status updates, etc.
   */
  async sendProactive(
    platform: Platform,
    chatId: string,
    message: Omit<OutboundMessage, "platform" | "chatId">
  ): Promise<void> {
    const adapter = this.adapters.get(platform);
    if (!adapter) {
      throw new Error(`No adapter registered for platform: ${platform}`);
    }

    await adapter.sendMessage({
      ...message,
      platform,
      chatId,
    });
  }

  /**
   * Deliver a file to a user on any platform.
   */
  async deliverFile(
    platform: Platform,
    chatId: string,
    fileUrl: string,
    fileName: string,
    caption?: string
  ): Promise<void> {
    const adapter = this.adapters.get(platform);
    if (!adapter) {
      throw new Error(`No adapter registered for platform: ${platform}`);
    }

    await adapter.sendDocument(chatId, fileUrl, fileName, caption);
  }

  /**
   * Get all registered platform names.
   */
  getRegisteredPlatforms(): Platform[] {
    return Array.from(this.adapters.keys());
  }

  /**
   * Clean up stale sessions (older than the given threshold in hours).
   */
  cleanStaleSessions(maxAgeHours: number = 72): number {
    const cutoff = new Date(Date.now() - maxAgeHours * 60 * 60 * 1000);
    let cleaned = 0;

    for (const [key, session] of this.sessions.entries()) {
      if (new Date(session.lastActivity) < cutoff) {
        this.sessions.delete(key);
        cleaned++;
      }
    }

    return cleaned;
  }
}
