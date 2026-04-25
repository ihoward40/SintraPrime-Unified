import { z } from "zod";

const HttpStatusExpectedSchema = z
  .union([z.number(), z.array(z.number())])
  .transform((v) => (Array.isArray(v) ? v : [v]));

const StepGuardSchema = z.object({
  path: z.string().min(1),
  op: z.enum(["==", "!=" as const]),
  value: z.any(),
});

export const ExecutionStepSchema = z.object({
  step_id: z.string(),
  action: z.string(),
  adapter: z.enum([
    "WebhookAdapter",
    "NotionAdapter",
    "GoogleDriveAdapter",
    "MakeAdapter",
    "SlackAdapter",
    "BuildMyAgentAdapter",
    "BrowserOperatorAdapter",
  ]),
  method: z.enum(["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]),
  read_only: z.boolean().optional(),
  url: z.string().url(),
  notion_path: z.string().optional(),
  notion_path_prestate: z.string().optional(),
  approval_scoped: z.boolean().optional(),
  approved_at: z.string().optional(),
  prestate: z.any().optional(),
  prestate_fingerprint: z.string().optional(),
  properties: z.any().optional(),
  guards: z.array(StepGuardSchema).optional(),
  headers: z.record(z.string(), z.string()).optional(),
  payload: z.any().optional(),
  expects: z.object({
    http_status: HttpStatusExpectedSchema,
    json_paths_present: z.array(z.string()).optional(),
  }),
  idempotency_key: z.string().nullable().optional(),
  rollback: z.any().optional(),
});

export const ExecutionPhaseSchema = z.object({
  phase_id: z.string().min(1),
  required_capabilities: z.array(z.string()).min(1),
  inputs_from: z.array(z.string()).optional(),
  steps: z.array(ExecutionStepSchema).min(1),
  // Planner-declared outputs that should be captured into artifacts for later phases.
  outputs: z.array(z.string()).optional(),
});

export const ExecutionPlanSchema = z
  .object({
  kind: z.literal("ExecutionPlan"),
  execution_id: z.string(),
  threadId: z.string(),
  dry_run: z.boolean(),
  goal: z.string(),
  // Tier 5.1: capability requirements (planner emits requirements, CLI resolves via registry).
  required_capabilities: z.array(z.string()).optional(),
  agent_versions: z.object({
    validator: z.string(),
    planner: z.string(),
  }),
  assumptions: z.array(z.string()).optional(),
  required_secrets: z.array(
    z.object({
      name: z.string(),
      source: z.literal("env"),
      notes: z.string(),
    })
  ),
  // Tier 5.2: phased execution is optional and additive.
  phases: z.array(ExecutionPhaseSchema).optional(),
  // Legacy single-phase steps. If phases are present, steps may be omitted.
  steps: z.array(ExecutionStepSchema).optional().default([]),
  })
  .refine(
    (plan) => !(plan.phases && Array.isArray(plan.steps) && plan.steps.length > 0),
    {
      message: "ExecutionPlan cannot define both top-level steps and phases",
    }
  );

export const NeedInputSchema = z.object({
  kind: z.literal("NeedInput"),
  threadId: z.string().optional(),
  question: z.string(),
  missing: z.array(z.string()).optional(),
});

export const ValidatedCommandSchema = z.object({
  kind: z.literal("ValidatedCommand"),
  allowed: z.boolean(),
  threadId: z.string().optional(),
  intent: z.string().optional(),
  command: z.string().optional(),
  args: z.record(z.string(), z.any()).optional(),
  denial_reason: z.string().optional(),
  required_inputs: z.array(z.string()).optional(),
  // Optional: validator may override the forwarded command
  forwarded_command: z.string().optional(),
});

export const ValidatorOutputSchema = z.union([ValidatedCommandSchema, NeedInputSchema]);

export const PlannerOutputSchema = z.union([ExecutionPlanSchema, NeedInputSchema]);

export type ExecutionPlan = z.infer<typeof ExecutionPlanSchema>;
export type ExecutionStep = z.infer<typeof ExecutionStepSchema>;
export type ExecutionPhase = z.infer<typeof ExecutionPhaseSchema>;
export type NeedInput = z.infer<typeof NeedInputSchema>;
export type ValidatedCommand = z.infer<typeof ValidatedCommandSchema>;
export type ValidatorOutput = z.infer<typeof ValidatorOutputSchema>;
export type PlannerOutput = z.infer<typeof PlannerOutputSchema>;
