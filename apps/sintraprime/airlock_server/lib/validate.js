import crypto from "crypto";

function isHex64(s) {
  return typeof s === "string" && /^[a-f0-9]{64}$/i.test(s);
}

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

export function validatePayload(payload, maxFiles = 10) {
  if (!payload || typeof payload !== "object") throw new Error("Payload must be an object");
  
  // Guardrail: must explicitly confirm no submit/pay actions
  if (payload.no_submit_pay !== true) throw new Error("no_submit_pay must be true");
  
  if (typeof payload.task_id !== "string" || !payload.task_id.trim()) throw new Error("task_id required");
  if (typeof payload.task_title !== "string") payload.task_title = "Untitled Task";
  
  const files = Array.isArray(payload.files) ? payload.files : [];
  if (files.length > maxFiles) throw new Error(`Too many files (max ${maxFiles})`);
  
  for (const [i, f] of files.entries()) {
    if (!f || typeof f !== "object") throw new Error(`files[${i}] invalid`);
    if (typeof f.name !== "string" || !f.name.trim()) throw new Error(`files[${i}].name required`);
    if (typeof f.mime !== "string" || !f.mime.trim()) throw new Error(`files[${i}].mime required`);
    if (typeof f.data_b64 !== "string" || !f.data_b64.trim()) throw new Error(`files[${i}].data_b64 required`);
    
    const buf = Buffer.from(f.data_b64, "base64");
    const computed = sha256Hex(buf);
    
    if (f.bytes != null && Number(f.bytes) !== buf.length) {
      throw new Error(`files[${i}].bytes mismatch`);
    }
    if (!isHex64(f.sha256) || f.sha256.toLowerCase() !== computed.toLowerCase()) {
      throw new Error(`files[${i}].sha256 mismatch`);
    }
  }
  
  return true;
}
