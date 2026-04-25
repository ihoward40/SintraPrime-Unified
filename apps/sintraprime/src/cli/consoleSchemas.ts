import { z } from "zod";

export const SCHEMA_VERSION = "12.0" as const;

export const QueueItemSchema = z.object({
  execution_id: z.string(),
  status: z.string(),
  plan_hash: z.string().nullable(),
  created_at: z.string().nullable(),
  mode: z.enum(["BATCH_APPROVAL", "APPROVAL_GATED"]).nullable(),
  summary: z.string(),
});

export const QueueListSchema = z.object({
  kind: z.literal("QueueList"),
  schema_version: z.literal(SCHEMA_VERSION),
  pending: z.array(QueueItemSchema),
});

export const QueueItemJsonlSchema = z.object({
  execution_id: z.string(),
  status: z.string(),
  plan_hash: z.string().nullable().optional(),
});

export const RunPrestateItemSchema = z.object({
  step_id: z.string(),
  fingerprint: z.string(),
  artifact: z.string(),
});

export const RunDetailsSchema = z.object({
  kind: z.literal("RunDetails"),
  schema_version: z.literal(SCHEMA_VERSION),
  execution_id: z.string(),
  status: z.string().nullable(),
  plan_hash: z.string().nullable(),
  mode: z.enum(["BATCH_APPROVAL", "APPROVAL_GATED"]).nullable(),
  pending_step_ids: z.array(z.string()),
  agent_versions: z.record(z.string(), z.string()).optional(),
  prestate: z.array(RunPrestateItemSchema),
  artifacts: z.array(z.string()),
});

export const ArtifactIndexItemSchema = z.object({
  type: z.string(),
  path: z.string(),
});

export const ArtifactIndexSchema = z.object({
  kind: z.literal("ArtifactIndex"),
  schema_version: z.literal(SCHEMA_VERSION),
  execution_id: z.string(),
  artifacts: z.array(ArtifactIndexItemSchema),
});

export const RunTimelineEventSchema = z.object({
  timestamp: z.string(),
  event: z.string(),
});

export const RunTimelineSchema = z.object({
  kind: z.literal("RunTimeline"),
  schema_version: z.literal(SCHEMA_VERSION),
  execution_id: z.string(),
  events: z.array(RunTimelineEventSchema),
});

export const RunRejectedSchema = z.object({
  kind: z.literal("RunRejected"),
  execution_id: z.string(),
  reason: z.string(),
});

export function assertValid<T>(schema: z.ZodType<T>, value: unknown): T {
  return schema.parse(value);
}
