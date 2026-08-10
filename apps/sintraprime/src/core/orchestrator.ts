/**
 * Core Orchestrator - The brain of the autonomous agent system
 *
 * Responsibilities:
 * - Receive and validate task requests
 * - Generate execution plans
 * - Coordinate execution through the executor
 * - Handle human-in-the-loop escalation
 * - Maintain job state and checkpoints
 */

import { TaskRequest, Plan, PlanStep, JobState } from '../types/index.js';
import { PolicyGate } from '../governance/policyGate.js';
import { ReceiptLedger } from '../audit/receiptLedger.js';
import { Executor } from './executor.js';
import { Planner } from './planner.js';
import {
  attachTrustAuthorityRoute,
  evaluateTrustAuthorityStep,
  routeTrustAuthority,
  type TrustAuthorityRoute,
} from '../governance/trustAuthorityRouter.js';

export class Orchestrator {
  private policyGate: PolicyGate;
  private receiptLedger: ReceiptLedger;
  private executor: Executor;
  private planner: Planner;
  private jobs: Map<string, JobState> = new Map();

  constructor(
    policyGate: PolicyGate,
    receiptLedger: ReceiptLedger,
    executor: Executor,
    planner: Planner
  ) {
    this.policyGate = policyGate;
    this.receiptLedger = receiptLedger;
    this.executor = executor;
    this.planner = planner;
  }

  /**
   * Process a task request from start to finish.
   *
   * Trust-related requests are enriched with the Howard Trust Authority route
   * before planning. Legal-effect and external execution steps are then checked
   * again immediately before execution so a planner cannot bypass the gate.
   */
  async processTask(request: TaskRequest): Promise<JobState> {
    const jobId = this.generateJobId();
    const job: JobState = {
      id: jobId,
      planId: '',
      status: 'running',
      history: []
    };
    this.jobs.set(jobId, job);

    try {
      // Step 1: Validate the request
      await this.validateRequest(request);

      // Step 1A: Determine and attach trust authority routing before planning.
      const trustRoute = routeTrustAuthority(request);
      const governedRequest = attachTrustAuthorityRoute(request);

      if (trustRoute.isTrustRelated) {
        await this.receiptLedger.recordAction({
          id: this.generateReceiptId(),
          toolCallId: '',
          actor: 'trust_authority_router',
          action: 'trust_authority_route_attached',
          timestamp: new Date().toISOString(),
          result: {
            jobId: job.id,
            routeId: trustRoute.routeId,
            authorityOrder: trustRoute.authorityOrder,
            legalEffectRequested: trustRoute.legalEffectRequested,
            externalExecutionRequested: trustRoute.externalExecutionRequested,
            currentLawStatus: trustRoute.currentLawVerification.status,
            principalApproval: trustRoute.principalApproval,
            blockingReasons: trustRoute.blockingReasons,
          },
          hash: this.hashObject(trustRoute)
        });
      }

      // Step 2: Generate a plan from the governed request.
      const plan = await this.planner.generatePlan(governedRequest);
      job.planId = plan.id;

      await this.receiptLedger.recordAction({
        id: this.generateReceiptId(),
        toolCallId: '',
        actor: 'orchestrator',
        action: 'plan_created',
        timestamp: new Date().toISOString(),
        result: { planId: plan.id, stepCount: plan.steps.length },
        hash: this.hashObject(plan)
      });

      // Step 3: Execute the plan with the trust authority gate in front of the
      // ordinary policy gate.
      await this.executePlan(job, plan, trustRoute);

      // Step 4: Mark job as completed
      job.status = 'completed';
      await this.receiptLedger.recordAction({
        id: this.generateReceiptId(),
        toolCallId: '',
        actor: 'orchestrator',
        action: 'job_completed',
        timestamp: new Date().toISOString(),
        result: { jobId: job.id },
        hash: this.hashObject(job)
      });

      return job;
    } catch (error) {
      job.status = job.status === 'waiting-human' ? 'waiting-human' : 'failed';
      await this.receiptLedger.recordAction({
        id: this.generateReceiptId(),
        toolCallId: '',
        actor: 'orchestrator',
        action: job.status === 'waiting-human' ? 'job_waiting_human' : 'job_failed',
        timestamp: new Date().toISOString(),
        result: { jobId: job.id, error: String(error) },
        hash: this.hashObject(job)
      });
      throw error;
    }
  }

  /** Execute a plan step by step. */
  private async executePlan(
    job: JobState,
    plan: Plan,
    trustRoute: TrustAuthorityRoute,
  ): Promise<void> {
    for (const step of plan.steps) {
      if (!this.areDependenciesCompleted(step, job)) {
        throw new Error(`Dependencies not met for step ${step.id}`);
      }

      job.currentStepId = step.id;

      // Trust authority gate executes before the general tool policy gate.
      const trustDecision = evaluateTrustAuthorityStep(step, trustRoute);
      if (!trustDecision.allowed) {
        job.status = 'waiting-human';
        await this.receiptLedger.recordAction({
          id: this.generateReceiptId(),
          toolCallId: step.id,
          actor: 'trust_authority_gate',
          action: 'trust_execution_blocked',
          timestamp: new Date().toISOString(),
          result: {
            stepId: step.id,
            reason: trustDecision.reason,
            routeId: trustRoute.routeId,
            currentLawStatus: trustRoute.currentLawVerification.status,
            principalApproval: trustRoute.principalApproval,
          },
          hash: this.hashObject({ step, trustDecision, trustRoute })
        });
        throw new Error(trustDecision.reason ?? 'Execution blocked by trust authority gate');
      }

      // Existing policy gate remains authoritative for ordinary tool governance.
      const policyDecision = await this.policyGate.evaluate({
        id: this.generateToolCallId(),
        idempotencyKey: this.generateIdempotencyKey(),
        planStepId: step.id,
        tool: step.tool,
        args: step.args,
        timestamp: new Date().toISOString()
      });

      if (policyDecision.decision === 'block') {
        job.status = 'waiting-human';
        await this.receiptLedger.recordAction({
          id: this.generateReceiptId(),
          toolCallId: '',
          actor: 'policy_gate',
          action: 'execution_blocked',
          timestamp: new Date().toISOString(),
          result: { stepId: step.id, reason: policyDecision.reason },
          hash: this.hashObject(policyDecision)
        });
        throw new Error(`Execution blocked by policy: ${policyDecision.reason}`);
      }

      try {
        const result = await this.executor.executeStep(step);
        job.history.push({
          stepId: step.id,
          status: 'completed',
          result,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        job.history.push({
          stepId: step.id,
          status: 'failed',
          error: String(error),
          timestamp: new Date().toISOString()
        });
        throw error;
      }
    }
  }

  private async validateRequest(request: TaskRequest): Promise<void> {
    if (!request.id || !request.prompt) {
      throw new Error('Invalid task request: missing required fields');
    }
  }

  private areDependenciesCompleted(step: PlanStep, job: JobState): boolean {
    if (!step.dependencies || step.dependencies.length === 0) {
      return true;
    }

    return step.dependencies.every(depId =>
      job.history.some(h => h.stepId === depId && h.status === 'completed')
    );
  }

  async resumeJob(jobId: string): Promise<JobState> {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error(`Job not found: ${jobId}`);
    }

    if (job.status !== 'paused' && job.status !== 'waiting-human') {
      throw new Error(`Job cannot be resumed: current status is ${job.status}`);
    }

    job.status = 'running';
    return job;
  }

  async pauseJob(jobId: string): Promise<JobState> {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error(`Job not found: ${jobId}`);
    }

    job.status = 'paused';
    await this.receiptLedger.recordAction({
      id: this.generateReceiptId(),
      toolCallId: '',
      actor: 'orchestrator',
      action: 'job_paused',
      timestamp: new Date().toISOString(),
      result: { jobId: job.id },
      hash: this.hashObject(job)
    });

    return job;
  }

  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateReceiptId(): string {
    return `receipt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateToolCallId(): string {
    return `toolcall_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateIdempotencyKey(): string {
    return `idem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private hashObject(obj: any): string {
    return JSON.stringify(obj);
  }
}
