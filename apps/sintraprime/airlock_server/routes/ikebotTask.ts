// airlock_server/routes/ikebotTask.ts
// New webhook endpoint for the airlock server that receives tasks from ClawdBot,
// verifies the HMAC signature, generates a governance receipt, and forwards
// the task to the Make.com orchestration layer.

import crypto from "crypto";

export interface IkeBotTaskRequest {
  task_id: string;
  service_key: string;
  user_id: string;
  telegram_chat_id: number;
  subscription_tier: "free" | "pro" | "enterprise";
  payment_confirmed: boolean;
  stripe_payment_id: string;
  user_input: Record<string, string>;
  uploaded_files?: string[];
  created_at: string;
  priority: number;
}

export interface ExecutionReceipt {
  receipt_id: string;
  task_id: string;
  agent: string;
  action: string;
  status: "Pending" | "Executed" | "Failed";
  timestamp: string;
  payload_hash: string;
}

/**
 * Verify the HMAC-SHA256 signature of an incoming request.
 */
function verifySignature(payload: string, signature: string): boolean {
  const secret = process.env.AIRLOCK_HMAC_SECRET;
  if (!secret) return false;

  const expected = crypto
    .createHmac("sha256", secret)
    .update(payload)
    .digest("hex");

  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expected)
    );
  } catch {
    return false;
  }
}

/**
 * Generate a unique receipt ID.
 */
function generateReceiptId(): string {
  const uuid = crypto.randomUUID();
  return `RCP-${uuid}`;
}

/**
 * Handle an incoming IkeBot task request.
 * This function can be mounted as an Express route handler or used directly.
 *
 * @param headers - Request headers (must include x-signature and x-task-id)
 * @param body - Parsed JSON body of the request
 * @param logReceipt - Function to persist the receipt to the immutable ledger
 * @returns Response object with status and receipt_id
 */
export async function handleIkeBotTask(
  headers: Record<string, string | undefined>,
  body: IkeBotTaskRequest,
  logReceipt: (receipt: ExecutionReceipt) => Promise<void>
): Promise<{ status: number; body: any }> {
  const signature = headers["x-signature"];
  const rawBody = JSON.stringify(body);

  // 1. Verify HMAC signature
  if (!signature || !verifySignature(rawBody, signature)) {
    return {
      status: 401,
      body: { error: "Invalid signature" },
    };
  }

  // 2. Validate payment confirmation
  if (!body.payment_confirmed) {
    return {
      status: 402,
      body: { error: "Payment not confirmed" },
    };
  }

  // 3. Generate Execution Receipt
  const receipt: ExecutionReceipt = {
    receipt_id: generateReceiptId(),
    task_id: body.task_id,
    agent: "ikebot-manus",
    action: "task_submission",
    status: "Pending",
    timestamp: new Date().toISOString(),
    payload_hash: crypto
      .createHash("sha256")
      .update(rawBody)
      .digest("hex"),
  };

  // 4. Log receipt to immutable ledger
  await logReceipt(receipt);

  // 5. Forward to Make.com orchestration
  const makeWebhook = process.env.MAKE_WEBHOOK_IKEBOT;
  if (makeWebhook) {
    try {
      await fetch(makeWebhook, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...body,
          receipt_id: receipt.receipt_id,
        }),
      });
    } catch (error: any) {
      console.error(`[ikebotTask] Failed to forward to Make.com: ${error.message}`);
      // Don't fail the request — the receipt is already logged
    }
  }

  return {
    status: 202,
    body: {
      status: "accepted",
      receipt_id: receipt.receipt_id,
      task_id: body.task_id,
    },
  };
}
