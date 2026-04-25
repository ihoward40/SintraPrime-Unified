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
   * Process a task request from start to finish
   */
  async processTask(request: TaskRequest): Promise<JobState> {
    // Create a new job
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

      // Step 2: Generate a plan
      const plan = await this.planner.generatePlan(request);
      job.planId = plan.id;

      // Log the plan creation
      await this.receiptLedger.recordAction({
        id: this.generateReceiptId(),
        toolCallId: '',
        actor: 'orchestrator',
        action: 'plan_created',
        timestamp: new Date().toISOString(),
        result: { planId: plan.id, stepCount: plan.steps.length },
        hash: this.hashObject(plan)
      });

      // Step 3: Execute the plan
      await this.executePlan(job, plan);

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
      // Handle errors and mark job as failed
      job.status = 'failed';
      await this.receiptLedger.recordAction({
        id: this.generateReceiptId(),
        toolCallId: '',
        actor: 'orchestrator',
        action: 'job_failed',
        timestamp: new Date().toISOString(),
        result: { jobId: job.id, error: String(error) },
        hash: this.hashObject(job)
      });
      throw error;
    }
  }

  /**
   * Execute a plan step by step
   */
  private async executePlan(job: JobState, plan: Plan): Promise<void> {
    for (const step of plan.steps) {
      // Check if all dependencies are completed
      if (!this.areDependenciesCompleted(step, job)) {
        throw new Error(`Dependencies not met for step ${step.id}`);
      }

      // Update job state
      job.currentStepId = step.id;

      // Check policy gate before executing
      const policyDecision = await this.policyGate.evaluate({
        id: this.generateToolCallId(),
        idempotencyKey: this.generateIdempotencyKey(),
        planStepId: step.id,
        tool: step.tool,
        args: step.args,
        timestamp: new Date().toISOString()
      });

      if (policyDecision.decision === 'block') {
        // Pause job and wait for human intervention
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

      // Execute the step
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

  /**
   * Validate a task request
   */
  private async validateRequest(request: TaskRequest): Promise<void> {
    if (!request.id || !request.prompt) {
      throw new Error('Invalid task request: missing required fields');
    }
  }

  /**
   * Check if all dependencies for a step are completed
   */
  private areDependenciesCompleted(step: PlanStep, job: JobState): boolean {
    if (!step.dependencies || step.dependencies.length === 0) {
      return true;
    }

    return step.dependencies.every(depId =>
      job.history.some(h => h.stepId === depId && h.status === 'completed')
    );
  }

  /**
   * Resume a paused job
   */
  async resumeJob(jobId: string): Promise<JobState> {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error(`Job not found: ${jobId}`);
    }

    if (job.status !== 'paused' && job.status !== 'waiting-human') {
      throw new Error(`Job cannot be resumed: current status is ${job.status}`);
    }

    job.status = 'running';
    // Continue execution from where it left off
    // (Implementation would need to reconstruct the plan and continue)
    return job;
  }

  /**
   * Pause a running job
   */
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

  // Helper methods
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
    // Simple hash implementation - in production, use crypto.createHash
    return JSON.stringify(obj);
  }
}
