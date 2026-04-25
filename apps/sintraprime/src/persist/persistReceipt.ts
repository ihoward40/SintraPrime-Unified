import fs from "node:fs";
import path from "node:path";

export type ReceiptLike = Record<string, unknown> & { kind: string };

export async function persistReceipt(receipt: ReceiptLike) {
  const persistLocal = process.env.PERSIST_LOCAL_RECEIPTS === "1";

  const writeLocal = () => {
    const runsDir = path.join(process.cwd(), "runs");
    fs.mkdirSync(runsDir, { recursive: true });
    const file = path.join(runsDir, "receipts.jsonl");
    fs.appendFileSync(file, `${JSON.stringify(receipt)}\n`, { encoding: "utf8" });
  };

  const url = process.env.NOTION_RUNS_WEBHOOK;
  if (!url) {
    writeLocal();
    return;
  }

  if (persistLocal) {
    writeLocal();
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(receipt),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`persistReceipt failed (${res.status}): ${text}`);
  }
}
