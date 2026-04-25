/**
 * Browser Automation Runner - Executes browser-based tasks
 * 
 * Uses Playwright for reliable browser automation with:
 * - Screenshot capture for debugging
 * - Human-in-the-loop for captchas and 2FA
 * - Checkpoint/resume capability
 */

import { Page, Browser, chromium } from 'playwright';

export interface BrowserTask {
  id: string;
  url: string;
  actions: BrowserAction[];
  checkpoints?: string[];
}

export interface BrowserAction {
  type: 'navigate' | 'click' | 'type' | 'wait' | 'screenshot' | 'extract' | 'scroll';
  selector?: string;
  value?: string;
  timeout?: number;
}

export interface BrowserRunnerConfig {
  headless?: boolean;
  screenshotDir?: string;
  userDataDir?: string; // For persistent sessions
}

export class BrowserRunner {
  private config: BrowserRunnerConfig;
  private browser?: Browser;
  private page?: Page;

  constructor(config: BrowserRunnerConfig = {}) {
    this.config = {
      headless: true,
      screenshotDir: './screenshots',
      ...config
    };
  }

  /**
   * Initialize the browser
   */
  async initialize(): Promise<void> {
    this.browser = await chromium.launch({
      headless: this.config.headless,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await this.browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 }
    });

    this.page = await context.newPage();
  }

  /**
   * Execute a browser task
   */
  async executeTask(task: BrowserTask): Promise<any> {
    if (!this.page) {
      await this.initialize();
    }

    const results: any[] = [];

    try {
      // Navigate to the starting URL
      await this.page!.goto(task.url, { waitUntil: 'networkidle' });
      await this.takeScreenshot(`${task.id}_start`);

      // Execute each action
      for (let i = 0; i < task.actions.length; i++) {
        const action = task.actions[i];
        
        if (!action) {
          results.push({ action: i, success: false, error: 'Action is undefined' });
          continue;
        }
        
        try {
          const result = await this.executeAction(action, i);
          results.push({ action: i, success: true, result });

          // Check if this is a checkpoint
          if (task.checkpoints?.includes(`action_${i}`)) {
            await this.takeScreenshot(`${task.id}_checkpoint_${i}`);
          }
        } catch (error) {
          // Take error screenshot
          await this.takeScreenshot(`${task.id}_error_${i}`);
          
          // Check if this requires human intervention
          if (this.requiresHumanIntervention(error)) {
            throw new Error(`Human intervention required at action ${i}: ${error}`);
          }

          results.push({ action: i, success: false, error: String(error) });
          throw error;
        }
      }

      // Take final screenshot
      await this.takeScreenshot(`${task.id}_complete`);

      return {
        taskId: task.id,
        success: true,
        results
      };
    } catch (error) {
      return {
        taskId: task.id,
        success: false,
        error: String(error),
        results
      };
    }
  }

  /**
   * Execute a single browser action
   */
  private async executeAction(action: BrowserAction, index: number): Promise<any> {
    if (!this.page) {
      throw new Error('Browser not initialized');
    }

    switch (action.type) {
      case 'navigate':
        await this.page.goto(action.value!, { waitUntil: 'networkidle' });
        return { url: this.page.url() };

      case 'click':
        await this.page.click(action.selector!, { timeout: action.timeout || 30000 });
        return { clicked: action.selector };

      case 'type':
        await this.page.fill(action.selector!, action.value!, { timeout: action.timeout || 30000 });
        return { typed: action.selector };

      case 'wait':
        if (action.selector) {
          await this.page.waitForSelector(action.selector, { timeout: action.timeout || 30000 });
        } else {
          await this.page.waitForTimeout(action.timeout || 1000);
        }
        return { waited: action.timeout };

      case 'screenshot':
        const screenshotPath = await this.takeScreenshot(action.value || `action_${index}`);
        return { screenshot: screenshotPath };

      case 'extract':
        const content = await this.page.textContent(action.selector!);
        return { extracted: content };

      case 'scroll':
        await this.page.evaluate(() => {
          // @ts-ignore - window is available in browser context
          window.scrollBy(0, window.innerHeight);
        });
        return { scrolled: true };

      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }

  /**
   * Take a screenshot
   */
  private async takeScreenshot(name: string): Promise<string> {
    if (!this.page) {
      throw new Error('Browser not initialized');
    }

    const path = `${this.config.screenshotDir}/${name}_${Date.now()}.png`;
    await this.page.screenshot({ path, fullPage: true });
    return path;
  }

  /**
   * Check if an error requires human intervention
   */
  private requiresHumanIntervention(error: any): boolean {
    const errorString = String(error).toLowerCase();
    
    // Common patterns that require human help
    const patterns = [
      'captcha',
      'recaptcha',
      '2fa',
      'two-factor',
      'verification code',
      'security check',
      'unusual activity'
    ];

    return patterns.some(pattern => errorString.includes(pattern));
  }

  /**
   * Pause execution and wait for human
   */
  async pauseForHuman(message: string): Promise<void> {
    console.log(`\n⚠️  Human intervention required: ${message}`);
    console.log('The browser will remain open. Press Enter when ready to continue...\n');
    
    // In a real implementation, this would integrate with the approval UI
    // For now, we'll just wait
    await new Promise(resolve => {
      process.stdin.once('data', resolve);
    });
  }

  /**
   * Save checkpoint
   */
  async saveCheckpoint(taskId: string, actionIndex: number): Promise<void> {
    // In a real implementation, this would save the browser state
    // For now, we'll just take a screenshot
    await this.takeScreenshot(`${taskId}_checkpoint_${actionIndex}`);
  }

  /**
   * Resume from checkpoint
   */
  async resumeFromCheckpoint(taskId: string, actionIndex: number): Promise<void> {
    // In a real implementation, this would restore the browser state
    console.log(`Resuming task ${taskId} from action ${actionIndex}`);
  }

  /**
   * Close the browser
   */
  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = undefined;
      this.page = undefined;
    }
  }
}
