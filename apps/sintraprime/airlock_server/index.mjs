#!/usr/bin/env node
/**
 * SintraPrime Airlock Server (ManusLite)
 * 
 * Production-ready HMAC-verified gateway between portal automation scripts
 * and Make.com workflows. Validates payloads, verifies signatures, sanitizes
 * receipts, and provides temporary file storage for Make to download.
 */

import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { hmacHex } from "./lib/hmac.js";
import { validatePayload } from "./lib/validate.js";
import { sanitizeReceipt } from "./lib/sanitize.js";
import { webhookLimiter, authFailureLimiter } from "./middleware/rate-limiter.mjs";
import { securityHeaders } from "./middleware/security.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Environment configuration
const PORT = process.env.PORT || 3000;
const MANUS_SHARED_SECRET = process.env.MANUS_SHARED_SECRET;
const MAKE_WEBHOOK_URL = process.env.MAKE_WEBHOOK_URL;
const AIRLOCK_SHARED_SECRET = process.env.AIRLOCK_SHARED_SECRET;
const ACCEPT_ORIGIN = process.env.ACCEPT_ORIGIN || "*";
const MAX_BODY_BYTES = parseInt(process.env.MAX_BODY_BYTES || "10485760", 10);
const ALLOW_DEV_ROUTES = process.env.ALLOW_DEV_ROUTES === "true";
const TIMESTAMP_WINDOW_SECONDS = parseInt(process.env.TIMESTAMP_WINDOW_SECONDS || "300", 10);
const MAX_FILES_PER_PAYLOAD = parseInt(process.env.MAX_FILES_PER_PAYLOAD || "10", 10);

// Validate required environment variables
if (!MANUS_SHARED_SECRET) {
  console.error("ERROR: MANUS_SHARED_SECRET environment variable is required");
  process.exit(1);
}

if (!MAKE_WEBHOOK_URL) {
  console.error("ERROR: MAKE_WEBHOOK_URL environment variable is required");
  process.exit(1);
}

if (!AIRLOCK_SHARED_SECRET) {
  console.error("ERROR: AIRLOCK_SHARED_SECRET environment variable is required");
  process.exit(1);
}

const app = express();

// Trust proxy for rate limiting (when behind Render/nginx)
app.set('trust proxy', 1);

// Apply security headers (skip for health check)
app.use((req, res, next) => {
  if (req.path === "/health") return next();
  securityHeaders(req, res, next);
});

// CORS middleware
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", ACCEPT_ORIGIN);
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type, x-manus-timestamp, x-manus-signature");
  
  if (req.method === "OPTIONS") {
    return res.sendStatus(200);
  }
  
  next();
});

// Body parser with size limit
app.use(express.json({ limit: MAX_BODY_BYTES }));

// Temporary file storage directory
const TEMP_DIR = path.join(__dirname, "tmp", "files");
fs.mkdirSync(TEMP_DIR, { recursive: true });

// Health check endpoint for Render (NO rate limiting or security headers)
app.get("/health", (req, res) => {
  res.status(200).json({
    status: "healthy",
    service: "sintraprime-airlock",
    version: "1.1.0",
    timestamp: new Date().toISOString()
  });
});

// Main webhook endpoint with rate limiting and auth failure tracking
app.post("/manus/webhook", webhookLimiter, authFailureLimiter, async (req, res) => {
  const startTime = Date.now();
  
  try {
    // Extract HMAC headers
    const timestamp = req.headers["x-manus-timestamp"];
    const signature = req.headers["x-manus-signature"];
    
    if (!timestamp || !signature) {
      console.error("Missing HMAC headers");
      return res.status(401).json({ error: "Missing authentication headers" });
    }
    
    // Verify timestamp is recent (configurable window, default 5 minutes)
    const now = Math.floor(Date.now() / 1000);
    const ts = parseInt(timestamp, 10);
    if (isNaN(ts) || Math.abs(now - ts) > TIMESTAMP_WINDOW_SECONDS) {
      console.error(`Timestamp out of range: ${timestamp} (now: ${now}, window: ${TIMESTAMP_WINDOW_SECONDS}s)`);
      return res.status(401).json({ error: "Timestamp out of range" });
    }
    
    // Verify HMAC signature
    const rawBody = JSON.stringify(req.body);
    const expectedSig = hmacHex(MANUS_SHARED_SECRET, `${timestamp}.${rawBody}`);
    
    if (signature !== expectedSig) {
      console.error("HMAC signature verification failed");
      return res.status(401).json({ error: "Invalid signature" });
    }
    
    console.log(`✓ HMAC verified for task ${req.body.task_id || "unknown"}`);
    
    // Validate payload structure
    try {
      validatePayload(req.body, MAX_FILES_PER_PAYLOAD);
      console.log(`✓ Payload validated for task ${req.body.task_id}`);
    } catch (err) {
      console.error(`Validation failed: ${err.message}`);
      return res.status(400).json({ error: `Validation failed: ${err.message}` });
    }
    
    // Store files temporarily for Make to download
    const taskId = req.body.task_id;
    const taskDir = path.join(TEMP_DIR, taskId);
    fs.mkdirSync(taskDir, { recursive: true });
    
    const files = req.body.files || [];
    for (const file of files) {
      const filePath = path.join(taskDir, file.name);
      const buffer = Buffer.from(file.data_b64, "base64");
      fs.writeFileSync(filePath, buffer);
      console.log(`  Stored: ${file.name} (${buffer.length} bytes)`);
    }
    
    // Sanitize receipt (strip base64 data)
    const receipt = sanitizeReceipt(req.body);
    
    // Add file download URLs for Make
    if (Array.isArray(receipt.files)) {
      const baseUrl = req.protocol + "://" + req.get("host");
      receipt.files = receipt.files.map(f => ({
        ...f,
        download_url: `${baseUrl}/files/${taskId}/${encodeURIComponent(f.name)}`
      }));
    }
    
    // Generate HMAC for Airlock→Make
    const receiptRaw = JSON.stringify(receipt);
    const airlockTs = Math.floor(Date.now() / 1000).toString();
    const airlockSig = hmacHex(AIRLOCK_SHARED_SECRET, `${airlockTs}.${receiptRaw}`);
    
    // Forward to Make.com
    console.log(`→ Forwarding to Make: ${MAKE_WEBHOOK_URL}`);
    const makeRes = await fetch(MAKE_WEBHOOK_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-airlock-timestamp": airlockTs,
        "x-airlock-signature": airlockSig
      },
      body: receiptRaw
    });
    
    const makeStatus = makeRes.status;
    const makeText = await makeRes.text();
    
    console.log(`← Make response: ${makeStatus}`);
    
    if (makeStatus >= 400) {
      console.error(`Make error: ${makeText}`);
      return res.status(502).json({ 
        error: "Make.com webhook failed", 
        make_status: makeStatus,
        make_response: makeText
      });
    }
    
    const elapsed = Date.now() - startTime;
    console.log(`✓ Success for task ${taskId} (${elapsed}ms)`);
    
    res.status(200).json({
      success: true,
      task_id: taskId,
      files_stored: files.length,
      forwarded_to_make: true,
      elapsed_ms: elapsed
    });
    
  } catch (err) {
    console.error("Webhook error:", err);
    res.status(500).json({ error: "Internal server error", message: err.message });
  }
});

// File download endpoint for Make.com (rate limited)
app.get("/files/:task_id/:filename", webhookLimiter, (req, res) => {
  const { task_id, filename } = req.params;
  const filePath = path.join(TEMP_DIR, task_id, filename);
  
  if (!fs.existsSync(filePath)) {
    console.error(`File not found: ${filePath}`);
    return res.status(404).json({ error: "File not found" });
  }
  
  console.log(`Serving file: ${task_id}/${filename}`);
  res.sendFile(filePath);
});

// Dev routes (only enabled if ALLOW_DEV_ROUTES=true)
if (ALLOW_DEV_ROUTES) {
  app.get("/dev/files", webhookLimiter, (req, res) => {
    const tasks = fs.existsSync(TEMP_DIR) 
      ? fs.readdirSync(TEMP_DIR).filter(f => {
          const stat = fs.statSync(path.join(TEMP_DIR, f));
          return stat.isDirectory();
        })
      : [];
    
    const result = {};
    for (const taskId of tasks) {
      const taskPath = path.join(TEMP_DIR, taskId);
      const files = fs.readdirSync(taskPath);
      result[taskId] = files;
    }
    
    res.json(result);
  });
  
  console.log("⚠️  Dev routes enabled");
}

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

// Start server
app.listen(PORT, () => {
  console.log(`🔒 Airlock server running on port ${PORT}`);
  console.log(`   Environment: ${process.env.NODE_ENV || "development"}`);
  console.log(`   Max body size: ${MAX_BODY_BYTES} bytes`);
  console.log(`   Max files per payload: ${MAX_FILES_PER_PAYLOAD}`);
  console.log(`   Timestamp window: ${TIMESTAMP_WINDOW_SECONDS}s`);
  console.log("   Rate limiting: express-rate-limit (100 req/min webhooks, 5 auth failures/15min)");
  console.log(`   CORS origin: ${ACCEPT_ORIGIN}`);
  console.log(`   Make webhook: ${MAKE_WEBHOOK_URL}`);
  console.log(`   Temp storage: ${TEMP_DIR}`);
});
