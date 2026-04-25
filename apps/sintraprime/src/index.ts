/**
 * SintraPrime Autonomous Agent - Main Entry Point
 * 
 * This file initializes and integrates all components of the system.
 */

import { Orchestrator } from './core/orchestrator.js';
import { Planner } from './core/planner.js';
import { Executor } from './core/executor.js';
import { PolicyGate } from './governance/policyGate.js';
import { ReceiptLedger } from './audit/receiptLedger.js';
import { SecretsVault } from './security/secretsVault.js';
import { ToolRegistry } from './tools/toolRegistry.js';
import { BrowserRunner } from './automation/browserRunner.js';
import { JobScheduler } from './scheduler/jobScheduler.js';
import { ReportingEngine } from './reporting/reportingEngine.js';
import { HowardTrustNavigator } from './agents/howardTrustNavigator.js';
import { AIFeatures } from './ai/aiFeatures.js';

// Connectors
import { ShopifyConnector } from './connectors/shopifyConnector.js';
import { MetaAdsConnector } from './connectors/metaAdsConnector.js';
import { GoogleDriveConnector } from './connectors/googleDriveConnector.js';
import { EmailConnector } from './connectors/emailConnector.js';

// SentinelGuard Cybersecurity Agent
import { SentinelGuardAgent } from './agents/sentinelGuard/sentinelGuardAgent.js';
import { NmapAdapter } from './tools/security/NmapAdapter.js';
import { OsintTool } from './tools/security/OsintTool.js';
import { PentestReportTool } from './tools/security/PentestReportTool.js';

/**
 * Initialize the SintraPrime system
 */
export async function initializeSintraPrime() {
  console.log('Initializing SintraPrime Autonomous Agent...');

  // 1. Initialize Secrets Vault
  const secretsVault = new SecretsVault({
    encryptionKey: process.env.SINTRAPRIME_ENCRYPTION_KEY,
    useEnvironment: true
  });
  await secretsVault.importFromEnvironment('SINTRAPRIME_');

  // 2. Initialize Receipt Ledger
  const receiptLedger = new ReceiptLedger({
    storageDir: './runs',
    enableChaining: true
  });

  // 3. Initialize Policy Gate
  const policyGate = new PolicyGate(
    {
      budgetPolicy: {
        id: 'default',
        name: 'Default Budget Policy',
        spendCaps: {
          daily: 1000,
          weekly: 5000,
          monthly: 20000
        },
        thresholds: {
          requiresApproval: 100
        },
        perToolLimits: {
          meta_ads: 500,
          shopify: 1000
        }
      },
      approvalThreshold: 100,
      highRiskActions: [
        'meta_ads_create_campaign',
        'shopify_delete_product',
        'email_send_bulk',
        'metasploit_exploit',
        'sqlmap_scan',
        'hydra_attack'
      ],
      autoApproveActions: [
        'web_search',
        'generate_report',
        'nmap_scan',
        'osint_gather'
      ]
    },
    receiptLedger
  );

  // 4. Initialize Tool Registry
  const toolRegistry = new ToolRegistry();

  // Register connectors as tools
  const shopifyConnector = new ShopifyConnector({
    shop: process.env.SHOPIFY_SHOP || '',
    accessToken: process.env.SHOPIFY_ACCESS_TOKEN || '',
    apiVersion: '2024-01'
  });

  const metaAdsConnector = new MetaAdsConnector({
    accessToken: process.env.META_ADS_ACCESS_TOKEN || '',
    adAccountId: process.env.META_ADS_AD_ACCOUNT_ID || '',
    apiVersion: 'v18.0'
  });

  const googleDriveConnector = new GoogleDriveConnector({
    accessToken: process.env.GOOGLE_DRIVE_ACCESS_TOKEN || ''
  });

  const emailConnector = new EmailConnector({
    type: 'gmail',
    accessToken: process.env.GMAIL_ACCESS_TOKEN || ''
  });

  // 5. Initialize Executor
  const executor = new Executor(toolRegistry, receiptLedger);

  // 6. Initialize Planner
  const planner = new Planner(null); // AI client would be initialized here

  // 7. Initialize Orchestrator
  const orchestrator = new Orchestrator(
    policyGate,
    receiptLedger,
    executor,
    planner
  );

  // 8. Initialize Browser Runner
  const browserRunner = new BrowserRunner({
    headless: true,
    screenshotDir: './screenshots'
  });

  // 9. Initialize Job Scheduler
  const jobScheduler = new JobScheduler();

  // 10. Initialize Reporting Engine
  const reportingEngine = new ReportingEngine(
    {
      schedule: 'daily at 4pm',
      recipients: ['admin@example.com'],
      format: 'markdown'
    },
    receiptLedger
  );

  // 11. Initialize Howard Trust Navigator
  const howardTrustNavigator = new HowardTrustNavigator(
    orchestrator,
    {
      trustName: 'ISIAH TARIK HOWARD TRUST',
      trustee: 'Isiah Tarik Howard',
      trustEIN: '92-6080121',
      businessName: 'IKE SOLUTIONS LLC',
      businessEIN: '87-1798434',
      beneficiaries: [
        {
          name: 'Latanya Winbush',
          email: 'lwinbush34@gmail.com',
          relationship: 'Mother of beneficiaries',
          status: 'active'
        }
      ],
      mailingAddress: 'c/o 991 Frelinghuysen Avenue, Apt 1K, Newark, NJ 07114'
    }
  );

  // 12. Initialize AI Features
  const aiFeatures = new AIFeatures({
    provider: 'openai',
    model: 'gpt-4',
    apiKey: process.env.OPENAI_API_KEY || '',
    features: {
      multimodal: true,
      reasoning: true,
      codeExecution: true,
      webSearch: true
    }
  });

  // 13. Register SentinelGuard security tools in the ToolRegistry
  toolRegistry.registerTool(new NmapAdapter());
  toolRegistry.registerTool(new OsintTool());
  toolRegistry.registerTool(new PentestReportTool(receiptLedger));

  // 14. Initialize SentinelGuard Cybersecurity Agent
  const scanTargets = (process.env.SENTINELGUARD_SCAN_TARGETS || '')
    .split(',')
    .map(t => t.trim())
    .filter(Boolean);

  const sentinelGuard = new SentinelGuardAgent({
    receiptLedger,
    policyGate,
    scheduler: jobScheduler,
    networkScanTargets: scanTargets,
    scanSchedule: process.env.SENTINELGUARD_SCAN_SCHEDULE || '0 2 * * 0',
    alertWebhook: process.env.SENTINELGUARD_ALERT_WEBHOOK,
  });

  // 15. Start SentinelGuard (non-blocking background service)
  await sentinelGuard.start();

  console.log('SintraPrime initialized successfully!');

  return {
    orchestrator,
    policyGate,
    receiptLedger,
    secretsVault,
    toolRegistry,
    browserRunner,
    jobScheduler,
    reportingEngine,
    howardTrustNavigator,
    aiFeatures,
    sentinelGuard,
    connectors: {
      shopify: shopifyConnector,
      metaAds: metaAdsConnector,
      googleDrive: googleDriveConnector,
      email: emailConnector
    }
  };
}

/**
 * Main entry point
 */
export async function main() {
  try {
    const system = await initializeSintraPrime();

    // Example: Process a task
    const taskResult = await system.orchestrator.processTask({
      id: 'task_001',
      prompt: 'Generate a daily report for today',
      priority: 'medium',
      requester: 'system',
      timestamp: new Date().toISOString()
    });

    console.log('Task completed:', taskResult);

    // Example: Generate a daily report
    const report = await system.reportingEngine.generateDailyReport();
    console.log('Daily report generated:', report);

    // Example: Generate Howard Trust operational plan
    const plan = await system.howardTrustNavigator.generateOperationalPlan();
    console.log('Operational plan:', plan);

  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

// Run if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
