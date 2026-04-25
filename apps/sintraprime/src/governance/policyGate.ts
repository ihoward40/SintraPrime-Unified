/**
 * Policy Gate - Evaluates whether actions should be allowed, blocked, or modified
 * 
 * This is the central governance component that enforces:
 * - Spending limits
 * - Approval requirements
 * - Safety constraints
 * - Compliance rules
 */

import { ToolCall, PolicyDecision, BudgetPolicy } from '../types/index.js';
import { ReceiptLedger } from '../audit/receiptLedger.js';

export interface PolicyGateConfig {
  budgetPolicy: BudgetPolicy;
  approvalThreshold: number;
  highRiskActions: string[];
  autoApproveActions: string[];
}

export class PolicyGate {
  private config: PolicyGateConfig;
  private receiptLedger: ReceiptLedger;
  private spendingTracker: Map<string, number> = new Map(); // tool -> amount spent

  constructor(config: PolicyGateConfig, receiptLedger: ReceiptLedger) {
    this.config = config;
    this.receiptLedger = receiptLedger;
  }

  /**
   * Evaluate a tool call and decide whether to allow, block, or modify it
   */
  async evaluate(toolCall: ToolCall): Promise<PolicyDecision> {
    const decisionId = this.generateDecisionId();
    const timestamp = new Date().toISOString();

    // Check 1: Is this a high-risk action?
    if (this.isHighRiskAction(toolCall.tool)) {
      const decision: PolicyDecision = {
        id: decisionId,
        toolCallId: toolCall.id,
        decision: 'block',
        reason: 'High-risk action requires human approval',
        timestamp
      };
      await this.recordDecision(decision);
      return decision;
    }

    // Check 2: Does this exceed spending limits?
    const spendCheck = await this.checkSpendingLimits(toolCall);
    if (!spendCheck.allowed) {
      const decision: PolicyDecision = {
        id: decisionId,
        toolCallId: toolCall.id,
        decision: 'block',
        reason: spendCheck.reason || 'Spending limit exceeded',
        timestamp
      };
      await this.recordDecision(decision);
      return decision;
    }

    // Check 3: Does this require approval based on threshold?
    if (this.requiresApproval(toolCall)) {
      const decision: PolicyDecision = {
        id: decisionId,
        toolCallId: toolCall.id,
        decision: 'block',
        reason: 'Action exceeds approval threshold',
        timestamp
      };
      await this.recordDecision(decision);
      return decision;
    }

    // Check 4: Should we modify the action for safety?
    const modification = this.checkForModifications(toolCall);
    if (modification) {
      const decision: PolicyDecision = {
        id: decisionId,
        toolCallId: toolCall.id,
        decision: 'modify',
        reason: 'Action modified for safety',
        timestamp,
        modifiedArgs: modification
      };
      await this.recordDecision(decision);
      return decision;
    }

    // All checks passed - allow the action
    const decision: PolicyDecision = {
      id: decisionId,
      toolCallId: toolCall.id,
      decision: 'allow',
      reason: 'All policy checks passed',
      timestamp
    };
    await this.recordDecision(decision);
    return decision;
  }

  /**
   * Check if an action is high-risk
   */
  private isHighRiskAction(tool: string): boolean {
    return this.config.highRiskActions.includes(tool);
  }

  /**
   * Check spending limits
   */
  private async checkSpendingLimits(toolCall: ToolCall): Promise<{ allowed: boolean; reason?: string }> {
    // Extract spending amount from tool call args
    const amount = this.extractSpendingAmount(toolCall);
    if (amount === 0) {
      return { allowed: true };
    }

    // Check per-tool limits
    const toolLimit = this.config.budgetPolicy.perToolLimits[toolCall.tool];
    if (toolLimit !== undefined) {
      const currentSpend = this.spendingTracker.get(toolCall.tool) || 0;
      if (currentSpend + amount > toolLimit) {
        return {
          allowed: false,
          reason: `Per-tool spending limit exceeded for ${toolCall.tool} (${currentSpend + amount} > ${toolLimit})`
        };
      }
    }

    // Check daily spending cap
    const totalDailySpend = Array.from(this.spendingTracker.values()).reduce((a, b) => a + b, 0);
    if (totalDailySpend + amount > this.config.budgetPolicy.spendCaps.daily) {
      return {
        allowed: false,
        reason: `Daily spending cap exceeded (${totalDailySpend + amount} > ${this.config.budgetPolicy.spendCaps.daily})`
      };
    }

    return { allowed: true };
  }

  /**
   * Extract spending amount from tool call arguments
   */
  private extractSpendingAmount(toolCall: ToolCall): number {
    // Look for common spending-related fields
    const args = toolCall.args;
    if (!args) return 0;

    // Check for various spending fields
    if (args.amount) return Number(args.amount);
    if (args.budget) return Number(args.budget);
    if (args.daily_budget) return Number(args.daily_budget);
    if (args.bid_amount) return Number(args.bid_amount);
    if (args.spend) return Number(args.spend);

    return 0;
  }

  /**
   * Check if action requires approval
   */
  private requiresApproval(toolCall: ToolCall): boolean {
    const amount = this.extractSpendingAmount(toolCall);
    return amount >= this.config.budgetPolicy.thresholds.requiresApproval;
  }

  /**
   * Check if action should be modified for safety
   */
  private checkForModifications(toolCall: ToolCall): any | null {
    // Example: Add safety flags to certain operations
    if (toolCall.tool === 'meta_ads' && toolCall.args.status === 'ACTIVE') {
      // Add a safety check before activating ads
      return {
        ...toolCall.args,
        _safety_check: true,
        _requires_review: true
      };
    }

    return null;
  }

  /**
   * Record spending for tracking
   */
  async recordSpending(tool: string, amount: number): Promise<void> {
    const currentSpend = this.spendingTracker.get(tool) || 0;
    this.spendingTracker.set(tool, currentSpend + amount);
  }

  /**
   * Record a policy decision
   */
  private async recordDecision(decision: PolicyDecision): Promise<void> {
    await this.receiptLedger.recordAction({
      id: this.generateReceiptId(),
      toolCallId: decision.toolCallId,
      actor: 'policy_gate',
      action: `policy_decision:${decision.decision}`,
      timestamp: decision.timestamp,
      result: decision,
      hash: this.hashObject(decision)
    });
  }

  /**
   * Reset spending tracker (called daily)
   */
  resetDailySpending(): void {
    this.spendingTracker.clear();
  }

  // Helper methods
  private generateDecisionId(): string {
    return `decision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateReceiptId(): string {
    return `receipt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private hashObject(obj: any): string {
    return JSON.stringify(obj);
  }
}
