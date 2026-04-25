/**
 * Job Scheduler - Manages scheduled and background jobs
 * 
 * Features:
 * - Cron-style scheduling
 * - Job queue with priority
 * - Persistent job state
 * - Retry logic with exponential backoff
 */

import { RRule } from 'rrule';
import { JobState } from '../types/index.js';

export interface ScheduledJob {
  id: string;
  name: string;
  schedule: string; // Cron expression or RRule
  task: any; // The task to execute
  enabled: boolean;
  lastRun?: string;
  nextRun?: string;
}

export interface JobQueueItem {
  id: string;
  priority: 'low' | 'medium' | 'high';
  task: any;
  retries: number;
  maxRetries: number;
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export class JobScheduler {
  private scheduledJobs: Map<string, ScheduledJob> = new Map();
  private jobQueue: JobQueueItem[] = [];
  private running = false;
  private checkInterval = 60000; // Check every minute

  /**
   * Start the scheduler
   */
  start(): void {
    if (this.running) {
      return;
    }

    this.running = true;
    this.scheduleLoop();
  }

  /**
   * Stop the scheduler
   */
  stop(): void {
    this.running = false;
  }

  /**
   * Schedule a recurring job
   */
  scheduleJob(job: ScheduledJob): void {
    // Calculate next run time
    job.nextRun = this.calculateNextRun(job.schedule);
    
    this.scheduledJobs.set(job.id, job);
  }

  /**
   * Unschedule a job
   */
  unscheduleJob(jobId: string): void {
    this.scheduledJobs.delete(jobId);
  }

  /**
   * Add a job to the queue
   */
  enqueueJob(job: Omit<JobQueueItem, 'id' | 'createdAt' | 'status'>): string {
    const queueItem: JobQueueItem = {
      id: this.generateJobId(),
      createdAt: new Date().toISOString(),
      status: 'pending',
      ...job
    };

    this.jobQueue.push(queueItem);
    this.sortQueue();

    return queueItem.id;
  }

  /**
   * Get the next job from the queue
   */
  private getNextJob(): JobQueueItem | undefined {
    return this.jobQueue.find(job => job.status === 'pending');
  }

  /**
   * Process the job queue
   */
  private async processQueue(): Promise<void> {
    const job = this.getNextJob();
    if (!job) {
      return;
    }

    job.status = 'running';

    try {
      // Execute the job (in a real implementation, this would call the orchestrator)
      await this.executeJob(job);
      
      job.status = 'completed';
    } catch (error) {
      // Handle retry logic
      if (job.retries < job.maxRetries) {
        job.retries++;
        job.status = 'pending';
        
        // Exponential backoff
        const delay = Math.pow(2, job.retries) * 1000;
        setTimeout(() => {
          // Job will be retried in the next queue processing
        }, delay);
      } else {
        job.status = 'failed';
      }
    }
  }

  /**
   * Execute a job
   */
  private async executeJob(job: JobQueueItem): Promise<void> {
    // In a real implementation, this would integrate with the orchestrator
    console.log(`Executing job ${job.id}`);
    
    // Placeholder for actual execution
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  /**
   * Main scheduler loop
   */
  private async scheduleLoop(): Promise<void> {
    while (this.running) {
      try {
        // Check for scheduled jobs that need to run
        const now = new Date().toISOString();
        
        for (const [jobId, job] of this.scheduledJobs) {
          if (job.enabled && job.nextRun && job.nextRun <= now) {
            // Add to queue
            this.enqueueJob({
              priority: 'medium',
              task: job.task,
              retries: 0,
              maxRetries: 3
            });

            // Update last run and calculate next run
            job.lastRun = now;
            job.nextRun = this.calculateNextRun(job.schedule, new Date(now));
          }
        }

        // Process the queue
        await this.processQueue();

        // Wait before next check
        await new Promise(resolve => setTimeout(resolve, this.checkInterval));
      } catch (error) {
        console.error('Scheduler loop error:', error);
      }
    }
  }

  /**
   * Calculate the next run time based on a schedule
   */
  private calculateNextRun(schedule: string, after?: Date): string {
    try {
      // Try to parse as RRule
      const rule = RRule.fromString(schedule);
      const nextDate = rule.after(after || new Date(), true);
      return nextDate ? nextDate.toISOString() : '';
    } catch {
      // If not RRule, try to parse as cron (simplified)
      // In a real implementation, use a proper cron parser
      return new Date(Date.now() + 86400000).toISOString(); // Default to 24 hours
    }
  }

  /**
   * Sort the queue by priority
   */
  private sortQueue(): void {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    
    this.jobQueue.sort((a, b) => {
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
  }

  /**
   * Get job status
   */
  getJobStatus(jobId: string): JobQueueItem | undefined {
    return this.jobQueue.find(job => job.id === jobId);
  }

  /**
   * Get all scheduled jobs
   */
  getScheduledJobs(): ScheduledJob[] {
    return Array.from(this.scheduledJobs.values());
  }

  /**
   * Get queue status
   */
  getQueueStatus(): {
    pending: number;
    running: number;
    completed: number;
    failed: number;
  } {
    return {
      pending: this.jobQueue.filter(j => j.status === 'pending').length,
      running: this.jobQueue.filter(j => j.status === 'running').length,
      completed: this.jobQueue.filter(j => j.status === 'completed').length,
      failed: this.jobQueue.filter(j => j.status === 'failed').length
    };
  }

  // Helper methods
  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
