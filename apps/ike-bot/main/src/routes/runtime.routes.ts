import { Router } from "express";
import { z } from "zod";
import {
  CapabilityId,
  evaluateAuthority,
  listCapabilities,
  selectModel,
} from "../runtime/governedRuntime";

const router = Router();

router.get("/capabilities", (_req, res) => {
  res.json({
    data: listCapabilities(),
    executionEnabled: false,
    note: "Discovery only. Side-effect execution must be wired to the canonical SintraPrime Principal/mission control plane before enablement.",
  });
});

const authorityRequest = z.object({
  principal: z.object({
    authenticated: z.boolean(),
    principalId: z.string().optional(),
    correlationId: z.string().min(1),
    approvedCapabilities: z.array(CapabilityId).optional(),
    maxRisk: z.enum(["observe", "draft", "reversible", "consequential"]).optional(),
  }),
  action: z.object({
    capability: CapabilityId,
    action: z.string().min(1),
    risk: z.enum(["observe", "draft", "reversible", "consequential", "prohibited"]).optional(),
    sideEffect: z.boolean(),
    draftOnly: z.boolean().optional(),
    estimatedCostUsd: z.number().nonnegative().optional(),
  }),
});

router.post("/evaluate-authority", (req, res) => {
  const parsed = authorityRequest.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid_request", details: parsed.error.flatten() });
  }
  return res.json({ decision: evaluateAuthority(parsed.data.principal, parsed.data.action) });
});

const modelRequest = z.object({
  candidates: z.array(z.object({
    id: z.string().min(1),
    provider: z.enum(["local", "openai", "anthropic", "google", "other"]),
    supportsVision: z.boolean().optional(),
    supportsTools: z.boolean().optional(),
    supportsLongContext: z.boolean().optional(),
    local: z.boolean().optional(),
    estimatedInputUsdPer1M: z.number().nonnegative().optional(),
    estimatedOutputUsdPer1M: z.number().nonnegative().optional(),
  })),
  policy: z.object({
    requireLocal: z.boolean().optional(),
    requireVision: z.boolean().optional(),
    requireTools: z.boolean().optional(),
    requireLongContext: z.boolean().optional(),
    maxInputUsdPer1M: z.number().nonnegative().optional(),
    maxOutputUsdPer1M: z.number().nonnegative().optional(),
  }),
});

router.post("/select-model", (req, res) => {
  const parsed = modelRequest.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid_request", details: parsed.error.flatten() });
  }
  return res.json({ selected: selectModel(parsed.data.candidates, parsed.data.policy) ?? null });
});

export default router;
