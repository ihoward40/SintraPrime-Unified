/**
 * Reporting Engine - Generates automated reports
 * 
 * Features:
 * - Daily summary reports
 * - KPI tracking
 * - Alert generation
 * - Multiple output formats (PDF, CSV, Markdown)
 */

import { ReportArtifact } from '../types/index.js';
import { ReceiptLedger } from '../audit/receiptLedger.js';

export interface ReportConfig {
  schedule: string; // e.g., 'daily at 4pm'
  recipients: string[];
  format: 'pdf' | 'csv' | 'markdown';
  includeCharts?: boolean;
}

export interface DailyReportData {
  date: string;
  summary: {
    totalJobs: number;
    completedJobs: number;
    failedJobs: number;
    totalSpend: number;
    actionsExecuted: number;
  };
  kpis: {
    successRate: number;
    avgExecutionTime: number;
    costPerAction: number;
  };
  alerts: Alert[];
  topActions: ActionSummary[];
  recommendations: string[];
}

export interface Alert {
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: string;
}

export interface ActionSummary {
  action: string;
  count: number;
  successRate: number;
  avgDuration: number;
}

export class ReportingEngine {
  private config: ReportConfig;
  private receiptLedger: ReceiptLedger;

  constructor(config: ReportConfig, receiptLedger: ReceiptLedger) {
    this.config = config;
    this.receiptLedger = receiptLedger;
  }

  /**
   * Generate a daily report
   */
  async generateDailyReport(date: string = new Date().toISOString().split('T')[0] ?? ''): Promise<ReportArtifact> {
    // Collect data for the report
    const data = await this.collectDailyData(date);

    // Generate the report in the specified format
    let content: any;
    switch (this.config.format) {
      case 'markdown':
        content = this.generateMarkdownReport(data);
        break;
      case 'csv':
        content = this.generateCSVReport(data);
        break;
      case 'pdf':
        content = await this.generatePDFReport(data);
        break;
      default:
        throw new Error(`Unsupported format: ${this.config.format}`);
    }

    const artifact: ReportArtifact = {
      id: this.generateReportId(),
      name: `Daily Report - ${date}`,
      timestamp: new Date().toISOString(),
      format: this.config.format,
      content
    };

    return artifact;
  }

  /**
   * Collect data for the daily report
   */
  private async collectDailyData(date: string): Promise<DailyReportData> {
    const startTime = `${date}T00:00:00.000Z`;
    const endTime = `${date}T23:59:59.999Z`;

    const receipts = this.receiptLedger.getReceiptsInRange(startTime, endTime);

    // Calculate summary metrics
    const jobReceipts = receipts.filter(r => r.action.startsWith('job_'));
    const completedJobs = jobReceipts.filter(r => r.action === 'job_completed').length;
    const failedJobs = jobReceipts.filter(r => r.action === 'job_failed').length;
    const totalJobs = completedJobs + failedJobs;

    const toolReceipts = receipts.filter(r => r.action.startsWith('tool_executed:'));
    const actionsExecuted = toolReceipts.length;

    // Calculate spending
    const totalSpend = this.calculateTotalSpend(receipts);

    // Calculate KPIs
    const successRate = totalJobs > 0 ? (completedJobs / totalJobs) * 100 : 0;
    const avgExecutionTime = this.calculateAvgExecutionTime(toolReceipts);
    const costPerAction = actionsExecuted > 0 ? totalSpend / actionsExecuted : 0;

    // Generate alerts
    const alerts = this.generateAlerts(receipts, { successRate, totalSpend });

    // Get top actions
    const topActions = this.getTopActions(toolReceipts);

    // Generate recommendations
    const recommendations = this.generateRecommendations({ successRate, totalSpend, actionsExecuted });

    return {
      date,
      summary: {
        totalJobs,
        completedJobs,
        failedJobs,
        totalSpend,
        actionsExecuted
      },
      kpis: {
        successRate,
        avgExecutionTime,
        costPerAction
      },
      alerts,
      topActions,
      recommendations
    };
  }

  /**
   * Generate a Markdown report
   */
  private generateMarkdownReport(data: DailyReportData): string {
    return `# Daily Report - ${data.date}

## Summary

- **Total Jobs:** ${data.summary.totalJobs}
- **Completed Jobs:** ${data.summary.completedJobs}
- **Failed Jobs:** ${data.summary.failedJobs}
- **Total Spend:** $${data.summary.totalSpend.toFixed(2)}
- **Actions Executed:** ${data.summary.actionsExecuted}

## Key Performance Indicators

- **Success Rate:** ${data.kpis.successRate.toFixed(1)}%
- **Avg Execution Time:** ${data.kpis.avgExecutionTime.toFixed(2)}s
- **Cost Per Action:** $${data.kpis.costPerAction.toFixed(4)}

## Alerts

${data.alerts.length > 0 ? data.alerts.map(alert => 
  `- **[${alert.severity.toUpperCase()}]** ${alert.message}`
).join('\n') : '_No alerts_'}

## Top Actions

${data.topActions.map((action, i) => 
  `${i + 1}. **${action.action}** - ${action.count} executions (${action.successRate.toFixed(1)}% success)`
).join('\n')}

## Recommendations

${data.recommendations.map(rec => `- ${rec}`).join('\n')}

---

*Report generated at ${new Date().toISOString()}*
`;
  }

  /**
   * Generate a CSV report
   */
  private generateCSVReport(data: DailyReportData): string {
    const rows = [
      ['Metric', 'Value'],
      ['Date', data.date],
      ['Total Jobs', data.summary.totalJobs],
      ['Completed Jobs', data.summary.completedJobs],
      ['Failed Jobs', data.summary.failedJobs],
      ['Total Spend', data.summary.totalSpend],
      ['Actions Executed', data.summary.actionsExecuted],
      ['Success Rate', data.kpis.successRate],
      ['Avg Execution Time', data.kpis.avgExecutionTime],
      ['Cost Per Action', data.kpis.costPerAction]
    ];

    return rows.map(row => row.join(',')).join('\n');
  }

  /**
   * Generate a PDF report (placeholder)
   */
  private async generatePDFReport(data: DailyReportData): Promise<any> {
    // In a real implementation, this would use a PDF library
    // For now, return the markdown content
    return this.generateMarkdownReport(data);
  }

  /**
   * Calculate total spending from receipts
   */
  private calculateTotalSpend(receipts: any[]): number {
    let total = 0;
    
    for (const receipt of receipts) {
      if (receipt.result && typeof receipt.result === 'object') {
        const spend = receipt.result.spend || receipt.result.amount || receipt.result.cost || 0;
        total += Number(spend);
      }
    }

    return total;
  }

  /**
   * Calculate average execution time
   */
  private calculateAvgExecutionTime(receipts: any[]): number {
    const durations = receipts
      .map(r => r.result?.duration)
      .filter(d => d !== undefined);

    if (durations.length === 0) return 0;

    const total = durations.reduce((a, b) => a + b, 0);
    return total / durations.length / 1000; // Convert to seconds
  }

  /**
   * Generate alerts based on data
   */
  private generateAlerts(receipts: any[], metrics: any): Alert[] {
    const alerts: Alert[] = [];

    // Check success rate
    if (metrics.successRate < 80) {
      alerts.push({
        severity: 'warning',
        message: `Success rate is below 80% (${metrics.successRate.toFixed(1)}%)`,
        timestamp: new Date().toISOString()
      });
    }

    // Check spending
    if (metrics.totalSpend > 1000) {
      alerts.push({
        severity: 'critical',
        message: `Daily spending exceeded $1000 ($${metrics.totalSpend.toFixed(2)})`,
        timestamp: new Date().toISOString()
      });
    }

    // Check for blocked actions
    const blockedActions = receipts.filter(r => r.action.includes('blocked'));
    if (blockedActions.length > 5) {
      alerts.push({
        severity: 'info',
        message: `${blockedActions.length} actions were blocked by policy gates`,
        timestamp: new Date().toISOString()
      });
    }

    return alerts;
  }

  /**
   * Get top actions by frequency
   */
  private getTopActions(receipts: any[]): ActionSummary[] {
    const actionMap = new Map<string, { count: number; successes: number; totalDuration: number }>();

    for (const receipt of receipts) {
      const action = receipt.action.replace('tool_executed:', '');
      const current = actionMap.get(action) || { count: 0, successes: 0, totalDuration: 0 };
      
      current.count++;
      if (receipt.result?.success) current.successes++;
      if (receipt.result?.duration) current.totalDuration += receipt.result.duration;

      actionMap.set(action, current);
    }

    const summaries: ActionSummary[] = [];
    for (const [action, data] of actionMap) {
      summaries.push({
        action,
        count: data.count,
        successRate: (data.successes / data.count) * 100,
        avgDuration: data.totalDuration / data.count / 1000
      });
    }

    // Sort by count and return top 5
    return summaries.sort((a, b) => b.count - a.count).slice(0, 5);
  }

  /**
   * Generate recommendations
   */
  private generateRecommendations(metrics: any): string[] {
    const recommendations: string[] = [];

    if (metrics.successRate < 90) {
      recommendations.push('Consider reviewing failed jobs to identify common issues');
    }

    if (metrics.totalSpend > 500) {
      recommendations.push('Review spending patterns and consider optimizing high-cost operations');
    }

    if (metrics.actionsExecuted < 10) {
      recommendations.push('Low activity detected - consider scheduling more automated tasks');
    }

    return recommendations;
  }

  // Helper methods
  private generateReportId(): string {
    return `report_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
