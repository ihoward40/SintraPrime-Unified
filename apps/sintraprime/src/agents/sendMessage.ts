import crypto from "node:crypto";
import { persistReceipt } from "../persist/persistReceipt.js";
import {
  finalizeLlmBudgetCall,
  readLlmBudgetConfig,
  reserveLlmBudgetCall,
} from "../llm/budget/llmBudget.js";

function mustString(v: unknown, name: string): string {
  if (typeof v !== "string" || v.trim() === "") {
    throw new Error(`Invalid ${name}: expected non-empty string`);
  }
  return v;
}

function tryExtractCreditsUsed(responseJson: any): number | null {
  const candidates: Array<Array<string>> = [
    ["Credits_Total"],
    ["credits_total"],
    ["credits"],
    ["usage", "credits"],
    ["usage", "credits_total"],
  ];

  for (const path of candidates) {
    let cur: any = responseJson;
    for (const k of path) {
      if (!cur || typeof cur !== "object") {
        cur = null;
        break;
      }
      cur = cur[k];
    }
    const n = Number(cur);
    if (Number.isFinite(n) && n >= 0) return n;
  }

  return null;
}

export type SendMessageInput = {
  message: string;
  threadId?: string;
  type?: "user_message";
  webhookUrl?: string;
  timeoutMs?: number;
};

export type SendMessageOutput = {
  status: number;
  ok: boolean;
  response: any;
};

export async function sendMessage(input: SendMessageInput): Promise<SendMessageOutput> {
  const message = mustString(input.message, "message");
  const threadId = mustString(input.threadId ?? "local_test_001", "threadId");
  const type = input.type ?? "user_message";

  const webhookUrl = input.webhookUrl ?? process.env.WEBHOOK_URL;
  if (!webhookUrl) throw new Error("Missing WEBHOOK_URL (arg or env var)");

  const secret = process.env.WEBHOOK_SECRET;
  if (!secret) throw new Error("Missing WEBHOOK_SECRET env var");

  const writeWebhookReceipts = process.env.WRITE_WEBHOOK_CALL_RECEIPTS === "1";
  const enableIdempotencyHeader = process.env.WEBHOOK_IDEMPOTENCY === "1";

  const timeoutMs = input.timeoutMs ?? 30_000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const requestBody = { type, threadId, message };
  const requestBodyText = JSON.stringify(requestBody);
  const requestBodySha256 = crypto.createHash("sha256").update(requestBodyText, "utf8").digest("hex");
  const messageSha256 = crypto.createHash("sha256").update(message, "utf8").digest("hex");

  const idempotencyKey = enableIdempotencyHeader
    ? crypto
        .createHash("sha256")
        .update(`${webhookUrl}|${requestBodySha256}`, "utf8")
        .digest("hex")
    : null;

  const budgetConfig = readLlmBudgetConfig();
  const estimatedCreditsCharged = budgetConfig.creditsPerCallEstimate;
  let budgetDateUtc: string | null = null;
  let budgetStateBefore: any = null;
  let budgetStateAfter: any = null;

  if (budgetConfig.enabled) {
    const decision = reserveLlmBudgetCall({ config: budgetConfig });
    budgetDateUtc = decision.date_utc;
    if (decision.allowed) {
      budgetStateBefore = decision.state_before;
      budgetStateAfter = decision.state_after_reservation;
      if (decision.config.writeReceipts) {
        try {
          await persistReceipt({
            kind: "LlmBudgetGateReceipt",
            ts: new Date().toISOString(),
            allowed: true,
            date_utc: decision.date_utc,
            webhook_url: webhookUrl,
            threadId,
            message_sha256: crypto.createHash("sha256").update(message, "utf8").digest("hex"),
            message_len: message.length,
            state_before: decision.state_before,
            state_after: decision.state_after_reservation,
            config: decision.config,
          });
        } catch {
          // ignore receipt failures
        }
      }
    } else {
      if (decision.config.writeReceipts) {
        try {
          await persistReceipt({
            kind: "LlmBudgetGateReceipt",
            ts: new Date().toISOString(),
            allowed: false,
            date_utc: decision.date_utc,
            code: decision.code,
            reason: decision.reason,
            webhook_url: webhookUrl,
            threadId,
            message_sha256: crypto.createHash("sha256").update(message, "utf8").digest("hex"),
            message_len: message.length,
            state: decision.state,
            config: decision.config,
          });
        } catch {
          // ignore receipt failures
        }
      }

      throw new Error(decision.reason);
    }
  }

  try {
    const startedAtMs = Date.now();
    const res = await fetch(webhookUrl, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Webhook-Secret": secret,
        "Cache-Control": "no-store",
        ...(idempotencyKey ? { "X-Idempotency-Key": idempotencyKey } : {}),
      },
      body: requestBodyText,
    });

    const text = await res.text();
    let json: any = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }

    if (json === null) {
      if (writeWebhookReceipts) {
        try {
          await persistReceipt({
            kind: "WebhookCallReceipt",
            receipt_id: crypto.randomUUID(),
            ts: new Date().toISOString(),
            webhook_url: webhookUrl,
            threadId,
            type,
            status: res.status,
            ok: res.ok,
            latency_ms: Date.now() - startedAtMs,
            timeout_ms: timeoutMs,
            idempotency_key: idempotencyKey,
            request_body_sha256: requestBodySha256,
            request_body_len: requestBodyText.length,
            message_sha256: messageSha256,
            message_len: message.length,
            response_text_sha256: crypto.createHash("sha256").update(text ?? "", "utf8").digest("hex"),
            response_text_len: String(text ?? "").length,
            parse_error: true,
          });
        } catch {
          // ignore receipt failures
        }
      }
      throw new Error(`Non-JSON response (${res.status}): ${text}`);
    }

    if (writeWebhookReceipts) {
      try {
        await persistReceipt({
          kind: "WebhookCallReceipt",
          receipt_id: crypto.randomUUID(),
          ts: new Date().toISOString(),
          webhook_url: webhookUrl,
          threadId,
          type,
          status: res.status,
          ok: res.ok,
          latency_ms: Date.now() - startedAtMs,
          timeout_ms: timeoutMs,
          idempotency_key: idempotencyKey,
          request_body_sha256: requestBodySha256,
          request_body_len: requestBodyText.length,
          message_sha256: messageSha256,
          message_len: message.length,
          response_json_sha256: crypto
            .createHash("sha256")
            .update(JSON.stringify(json), "utf8")
            .digest("hex"),
        });
      } catch {
        // ignore receipt failures
      }
    }

    if (budgetConfig.enabled && budgetDateUtc) {
      const actualCredits = tryExtractCreditsUsed(json);
      try {
        finalizeLlmBudgetCall({
          config: budgetConfig,
          date_utc: budgetDateUtc,
          estimated_credits_charged: estimatedCreditsCharged,
          actual_credits: actualCredits,
        });

        if (budgetConfig.writeReceipts) {
          await persistReceipt({
            kind: "LlmBudgetUsageReceipt",
            ts: new Date().toISOString(),
            date_utc: budgetDateUtc,
            webhook_url: webhookUrl,
            threadId,
            status: res.status,
            ok: res.ok,
            credits_used: actualCredits,
            estimated_credits_charged: estimatedCreditsCharged,
            budget_state_before: budgetStateBefore,
            budget_state_after_reservation: budgetStateAfter,
          });
        }
      } catch {
        // ignore budget finalize/receipt failures
      }
    }

    return { status: res.status, ok: res.ok, response: json };
  } finally {
    clearTimeout(timeout);
  }
}
