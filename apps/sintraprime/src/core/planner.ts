/**
 * Planner - Generates execution plans from task requests
 *
 * Uses AI to break down complex tasks into executable steps.
 */

import { TaskRequest, Plan, PlanStep } from '../types/index.js';

export class Planner {
  private aiClient: any;

  constructor(aiClient: any) {
    this.aiClient = aiClient;
  }

  async generatePlan(request: TaskRequest): Promise<Plan> {
    const planId = this.generatePlanId();
    const steps = await this.generateSteps(request);

    const plan: Plan = {
      id: planId,
      taskId: request.id,
      steps,
      constraints: this.extractConstraints(request)
    };

    return plan;
  }

  private async generateSteps(request: TaskRequest): Promise<PlanStep[]> {
    const trustRoute = request.context?.trustAuthorityRoute;
    const steps: PlanStep[] = [];
    let authorityDependency: string | undefined;

    if (trustRoute?.isTrustRelated) {
      const instrumentStepId = this.generateStepId();
      steps.push({
        id: instrumentStepId,
        description: 'Consult trust-instrument-authority for governing trust language',
        tool: 'analyze',
        args: {
          authorityStage: 'trust-instrument-authority',
          skill: 'trust-instrument-authority',
          task: request.prompt,
          requirement: 'Return exact trust-instrument support, approval rules, conflicts, and provenance.'
        },
        dependencies: []
      });

      const weissStepId = this.generateStepId();
      steps.push({
        id: weissStepId,
        description: 'Consult weisss-trustee-handbook as secondary educational authority',
        tool: 'analyze',
        args: {
          authorityStage: 'weisss-trustee-handbook',
          skill: 'weisss-trustee-handbook',
          task: request.prompt,
          requirement: 'Use only for issue spotting, workflow guidance, and research leads; do not treat as controlling law.'
        },
        dependencies: [instrumentStepId]
      });

      authorityDependency = weissStepId;

      if (trustRoute.legalEffectRequested || trustRoute.externalExecutionRequested) {
        const currentLawStepId = this.generateStepId();
        steps.push({
          id: currentLawStepId,
          description: 'Run current-law-verifier against current primary authority',
          tool: 'web_search',
          args: {
            authorityStage: 'current-law-verifier',
            task: request.prompt,
            jurisdiction: trustRoute.currentLawVerification?.jurisdiction,
            requirePrimarySources: true,
            outputContract: {
              status: 'VERIFIED_CURRENT | CONFLICT_FOUND | NOT_YET_VERIFIED',
              jurisdiction: 'string',
              authorities: 'string[]',
              verifiedAt: 'ISO-8601 timestamp',
              verifier: 'current-law-verifier'
            }
          },
          dependencies: [weissStepId]
        });
        authorityDependency = currentLawStepId;
      }
    }

    const analyzeStepId = this.generateStepId();
    steps.push({
      id: analyzeStepId,
      description: 'Analyze the task requirements',
      tool: 'analyze',
      args: {
        prompt: request.prompt,
        trustAuthorityRoute: trustRoute,
        mandatoryAuthorityInstructions: request.context?.mandatoryAuthorityInstructions ?? []
      },
      dependencies: authorityDependency ? [authorityDependency] : []
    });

    const executeStepId = this.generateStepId();
    steps.push({
      id: executeStepId,
      description: 'Execute the main task',
      tool: 'execute',
      args: {
        task: request.prompt,
        trustAuthorityRoute: trustRoute
      },
      dependencies: [analyzeStepId]
    });

    steps.push({
      id: this.generateStepId(),
      description: 'Generate a report',
      tool: 'create_document',
      args: {
        type: 'report',
        content: 'Task results',
        trustAuthorityRoute: trustRoute
      },
      dependencies: [executeStepId]
    });

    return steps;
  }

  private extractConstraints(request: TaskRequest): any {
    const trustRoute = request.context?.trustAuthorityRoute;
    return {
      maxBudget: 1000,
      maxDuration: 3600,
      requiresApproval:
        request.priority === 'high' ||
        Boolean(trustRoute?.externalExecutionRequested),
      trustAuthority: trustRoute
        ? {
            routeId: trustRoute.routeId,
            authorityOrder: trustRoute.authorityOrder,
            currentLawRequired:
              Boolean(trustRoute.legalEffectRequested) ||
              Boolean(trustRoute.externalExecutionRequested),
            principalApprovalRequired: Boolean(trustRoute.externalExecutionRequested),
            failClosed: true
          }
        : undefined
    };
  }

  private generatePlanId(): string {
    return `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateStepId(): string {
    return `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
