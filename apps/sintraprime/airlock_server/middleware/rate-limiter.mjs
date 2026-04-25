import rateLimit from "express-rate-limit";

export const webhookLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  message: { error: "Too many requests", retryAfter: "60 seconds" },
  standardHeaders: true,
  skipFailedRequests: true,
});

export const authFailureLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  skipSuccessfulRequests: true,
  message: { error: "Too many auth failures", retryAfter: "15 minutes" },
});
