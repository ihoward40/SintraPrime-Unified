/**
 * Receipt Ledger - Immutable audit trail for all actions
 * 
 * Records every action taken by the system with:
 * - Who performed the action
 * - What was done
 * - When it happened
 * - What the result was
 * - A cryptographic hash for integrity
 */

import { ActionReceipt } from '../types/index.js';
import * as crypto from 'crypto';
import * as fs from 'fs/promises';
import * as path from 'path';

export interface ReceiptLedgerConfig {
  storageDir: string;
  enableChaining?: boolean; // Link receipts with hash chains
}

export class ReceiptLedger {
  private config: ReceiptLedgerConfig;
  private receipts: ActionReceipt[] = [];
  private lastHash: string = '0000000000000000000000000000000000000000000000000000000000000000';

  constructor(config: ReceiptLedgerConfig) {
    this.config = config;
  }

  /**
   * Record an action in the ledger
   */
  async recordAction(receipt: ActionReceipt): Promise<void> {
    // Compute hash if not provided
    if (!receipt.hash) {
      receipt.hash = this.computeHash(receipt);
    }

    // Add to in-memory ledger
    this.receipts.push(receipt);

    // Persist to disk
    await this.persistReceipt(receipt);

    // Update last hash for chaining
    if (this.config.enableChaining) {
      this.lastHash = receipt.hash;
    }
  }

  /**
   * Compute a cryptographic hash of a receipt
   */
  private computeHash(receipt: ActionReceipt): string {
    const data = JSON.stringify({
      id: receipt.id,
      toolCallId: receipt.toolCallId,
      actor: receipt.actor,
      action: receipt.action,
      timestamp: receipt.timestamp,
      result: receipt.result,
      previousHash: this.config.enableChaining ? this.lastHash : undefined
    });

    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * Persist a receipt to disk
   */
  private async persistReceipt(receipt: ActionReceipt): Promise<void> {
    try {
      // Create storage directory if it doesn't exist
      await fs.mkdir(this.config.storageDir, { recursive: true });

      // Create a subdirectory for the date
      const date = new Date(receipt.timestamp);
      const dateDir = path.join(
        this.config.storageDir,
        date.getUTCFullYear().toString(),
        (date.getUTCMonth() + 1).toString().padStart(2, '0'),
        date.getUTCDate().toString().padStart(2, '0')
      );
      await fs.mkdir(dateDir, { recursive: true });

      // Write the receipt
      const filename = `${receipt.id}.json`;
      const filepath = path.join(dateDir, filename);
      await fs.writeFile(filepath, JSON.stringify(receipt, null, 2));

      // Write the hash sidecar
      const hashFilepath = path.join(dateDir, `${receipt.id}.sha256`);
      await fs.writeFile(hashFilepath, receipt.hash);
    } catch (error) {
      console.error('Failed to persist receipt:', error);
      // Don't throw - we don't want to fail the operation if logging fails
    }
  }

  /**
   * Get all receipts
   */
  getReceipts(): ActionReceipt[] {
    return [...this.receipts];
  }

  /**
   * Get receipts for a specific tool call
   */
  getReceiptsForToolCall(toolCallId: string): ActionReceipt[] {
    return this.receipts.filter(r => r.toolCallId === toolCallId);
  }

  /**
   * Get receipts by actor
   */
  getReceiptsByActor(actor: string): ActionReceipt[] {
    return this.receipts.filter(r => r.actor === actor);
  }

  /**
   * Get receipts by action
   */
  getReceiptsByAction(action: string): ActionReceipt[] {
    return this.receipts.filter(r => r.action === action);
  }

  /**
   * Get receipts in a time range
   */
  getReceiptsInRange(startTime: string, endTime: string): ActionReceipt[] {
    return this.receipts.filter(r => 
      r.timestamp >= startTime && r.timestamp <= endTime
    );
  }

  /**
   * Verify the integrity of a receipt
   */
  verifyReceipt(receipt: ActionReceipt): boolean {
    const computedHash = this.computeHash(receipt);
    return computedHash === receipt.hash;
  }

  /**
   * Verify the entire chain (if chaining is enabled)
   */
  verifyChain(): boolean {
    if (!this.config.enableChaining) {
      return true;
    }

    let previousHash = '0000000000000000000000000000000000000000000000000000000000000000';
    
    for (const receipt of this.receipts) {
      // Reconstruct the hash with the previous hash
      const data = JSON.stringify({
        id: receipt.id,
        toolCallId: receipt.toolCallId,
        actor: receipt.actor,
        action: receipt.action,
        timestamp: receipt.timestamp,
        result: receipt.result,
        previousHash
      });

      const computedHash = crypto.createHash('sha256').update(data).digest('hex');
      
      if (computedHash !== receipt.hash) {
        return false;
      }

      previousHash = receipt.hash;
    }

    return true;
  }

  /**
   * Export receipts to a court packet (PDF-ready format)
   */
  async exportCourtPacket(startTime: string, endTime: string): Promise<any> {
    const receipts = this.getReceiptsInRange(startTime, endTime);
    
    return {
      title: 'SintraPrime Audit Trail',
      period: { startTime, endTime },
      receiptCount: receipts.length,
      receipts: receipts.map(r => ({
        id: r.id,
        timestamp: r.timestamp,
        actor: r.actor,
        action: r.action,
        hash: r.hash
      })),
      verification: {
        chainValid: this.verifyChain(),
        allReceiptsValid: receipts.every(r => this.verifyReceipt(r))
      }
    };
  }
}
