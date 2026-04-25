/**
 * Slack Alert Formatter
 * Generates gold-standard Slack Block Kit messages for credit monitoring alerts
 * 
 * Responsibilities:
 * - Format alerts with appropriate severity emoji
 * - Create action buttons (Open Case, Open Run, Artifacts)
 * - Include auto-action context
 */

import type {
  RunRecordLegacy as RunRecord,
  Classification,
  SlackMessage,
  SlackActionsBlock,
  SeverityLevel,
} from "./types.js";

/**
 * Severity emoji mapping
 */
const SEVERITY_EMOJI: Record<SeverityLevel, string> = {
  SEV0: "🔥",
  SEV1: "🔴",
  SEV2: "🟡",
  SEV3: "🔵",
  SEV4: "⚪",
};

/**
 * Format an alert message for Slack
 */
export function formatAlert(
  runRecord: RunRecord,
  classification: Classification,
  caseUrl: string,
  runUrl: string
): SlackMessage {
  const emoji = SEVERITY_EMOJI[classification.severity];
  
  // Build header
  const headerText = `${emoji} ${classification.severity} • Credit Spike • ${runRecord.Scenario_Name}`;

  // Build action context based on policy actions
  const autoActions: string[] = [];
  if (classification.actions.includes("quarantine")) {
    autoActions.push("Quarantined artifacts");
  }
  if (classification.actions.includes("block_dispatch")) {
    autoActions.push("Downstream dispatch blocked");
  }
  if (classification.actions.includes("page_lock")) {
    autoActions.push("Notion page locked");
  }
  if (classification.actions.includes("require_ack_before_rerun")) {
    autoActions.push("Rerun requires acknowledgment");
  }

  const contextText = autoActions.length > 0
    ? `Auto-actions: ${autoActions.join(" / ")}`
    : "No automatic actions taken";

  // Build the Slack message
  const message: SlackMessage = {
    text: `${classification.severity} alert: ${runRecord.Scenario_Name} (${runRecord.Run_ID})`,
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: headerText,
          emoji: true,
        },
      },
      {
        type: "section",
        fields: [
          {
            type: "mrkdwn",
            text: `*Credits:* ${runRecord.Credits_Total.toLocaleString()} (Baseline ${runRecord.Baseline_Expected_Credits?.toLocaleString() ?? "N/A"}) → ${classification.varianceMultiplier.toFixed(2)}×`,
          },
          {
            type: "mrkdwn",
            text: `*Job Type:* ${runRecord.Job_Type}`,
          },
          {
            type: "mrkdwn",
            text: `*Misconfig Likelihood:* ${classification.misconfigLikelihood}`,
          },
          {
            type: "mrkdwn",
            text: `*Risk Flags:* ${formatRiskFlags(classification.riskFlags)}`,
          },
          {
            type: "mrkdwn",
            text: `*Run ID:* ${runRecord.Run_ID}`,
          },
          {
            type: "mrkdwn",
            text: `*Timestamp:* ${new Date(runRecord.Timestamp).toISOString()}`,
          },
        ],
      },
      {
        type: "actions",
        elements: [
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "Open Case",
              emoji: true,
            },
            url: caseUrl,
            style: classification.severity === "SEV0" ? "danger" : undefined,
          },
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "View Run",
              emoji: true,
            },
            url: runUrl,
          },
        ],
      },
      {
        type: "context",
        elements: [
          {
            type: "mrkdwn",
            text: contextText,
          },
        ],
      },
    ],
  };

  // Add artifacts button if available
  if (runRecord.Artifacts_Link) {
    const actionsBlock = message.blocks.find(
      (b): b is SlackActionsBlock => b.type === "actions"
    );
    if (actionsBlock) {
      actionsBlock.elements.push({
        type: "button",
        text: {
          type: "plain_text",
          text: "Artifacts",
          emoji: true,
        },
        url: runRecord.Artifacts_Link,
      });
    }
  }

  return message;
}

/**
 * Format risk flags for display
 */
function formatRiskFlags(riskFlags: string[]): string {
  if (riskFlags.length === 0) {
    return "None";
  }

  // Separate misconfig and legit flags
  const legitFlags = ["batch_job", "backfill_mode", "linear_scaling"];
  const misconfigFlags = riskFlags.filter(f => !legitFlags.includes(f));
  const positiveFlags = riskFlags.filter(f => legitFlags.includes(f));

  const parts: string[] = [];
  
  if (misconfigFlags.length > 0) {
    parts.push(misconfigFlags.map(f => f.replace(/_/g, " ")).join(", "));
  }
  
  if (positiveFlags.length > 0) {
    parts.push(`✓ ${positiveFlags.map(f => f.replace(/_/g, " ")).join(", ")}`);
  }

  return parts.join(" | ");
}

/**
 * Format a weekly credit review summary for Slack
 */
export function formatWeeklySummary(
  reportId: string,
  notionReportUrl: string,
  topScenarios: Array<{ scenario_id: string; total_credits: number; variance_multiplier: number }>,
  totalCredits: number,
  sev0Count: number,
  sev1Count: number
): SlackMessage {
  return {
    text: `Weekly Credit Review: ${reportId}`,
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: "📊 Weekly Credit Review",
          emoji: true,
        },
      },
      {
        type: "section",
        fields: [
          {
            type: "mrkdwn",
            text: `*Total Credits (7d):* ${totalCredits.toLocaleString()}`,
          },
          {
            type: "mrkdwn",
            text: `*SEV0 Incidents:* ${sev0Count}`,
          },
          {
            type: "mrkdwn",
            text: `*SEV1 Incidents:* ${sev1Count}`,
          },
          {
            type: "mrkdwn",
            text: `*Review Period:* ${reportId}`,
          },
        ],
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: "*Top Scenarios by Credit Spend:*\n" +
            topScenarios.slice(0, 5).map((s, i) => 
              `${i + 1}. ${s.scenario_id}: ${s.total_credits.toLocaleString()} credits (${s.variance_multiplier.toFixed(2)}× baseline)`
            ).join("\n"),
        },
      },
      {
        type: "actions",
        elements: [
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "View Full Report",
              emoji: true,
            },
            url: notionReportUrl,
            style: "primary",
          },
        ],
      },
    ],
  };
}

/**
 * Send Slack message (stub - would use webhook)
 */
export async function sendSlackAlert(
  message: SlackMessage,
  webhookUrl: string
): Promise<void> {
  console.log(`[slack-alert] Would send to ${webhookUrl}:`);
  console.log(JSON.stringify(message, null, 2));
  
  // In production, this would POST to the webhook:
  // await fetch(webhookUrl, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(message)
  // });
}
