import { z } from "zod";

const BrowserOperatorActionSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("navigate"),
    url: z.string().url().optional(),
    wait_until: z.enum(["load", "domcontentloaded", "networkidle0", "networkidle2"]).optional(),
    timeout_ms: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal("wait_for_selector"),
    selector: z.string().min(1),
    timeout_ms: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal("wait_ms"),
    ms: z.number().int().min(0).max(120_000),
  }),
  z.object({
    type: z.literal("click"),
    selector: z.string().min(1),
    timeout_ms: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal("type"),
    selector: z.string().min(1),
    text: z.string(),
    timeout_ms: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal("extract_text"),
    selector: z.string().min(1),
    key: z.string().min(1).optional(),
    timeout_ms: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal("screenshot"),
    name: z.string().min(1).optional(),
    full_page: z.boolean().optional(),
  }),
]);

export const BrowserOperatorPayloadSchema = z.object({
  actions: z.array(BrowserOperatorActionSchema).min(1),
  options: z
    .object({
      headless: z.boolean().optional(),
      viewport: z
        .object({
          width: z.number().int().positive().max(4096).optional(),
          height: z.number().int().positive().max(4096).optional(),
        })
        .optional(),
      slow_mo_ms: z.number().int().min(0).max(10_000).optional(),
      navigation_timeout_ms: z.number().int().positive().max(300_000).optional(),
      action_timeout_ms: z.number().int().positive().max(300_000).optional(),
    })
    .optional(),
});

export type BrowserOperatorPayload = z.infer<typeof BrowserOperatorPayloadSchema>;
export type BrowserOperatorAction = z.infer<typeof BrowserOperatorActionSchema>;
