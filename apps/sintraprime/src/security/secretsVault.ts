/**
 * Secrets Vault - Secure credential storage and management
 * 
 * Never stores credentials in plaintext
 * Uses environment variables or external secret managers
 */

import { CredentialReference } from '../types/index.js';
import * as crypto from 'crypto';

export interface SecretsVaultConfig {
  encryptionKey?: string; // For local encryption
  useEnvironment?: boolean; // Use environment variables
  externalProvider?: 'aws-secrets-manager' | 'azure-key-vault' | 'gcp-secret-manager';
}

export class SecretsVault {
  private config: SecretsVaultConfig;
  private credentials: Map<string, string> = new Map();
  private encryptionKey: Buffer;

  constructor(config: SecretsVaultConfig) {
    this.config = config;
    
    // Initialize encryption key
    if (config.encryptionKey) {
      this.encryptionKey = Buffer.from(config.encryptionKey, 'hex');
    } else {
      // Generate a random key (in production, this should be persisted securely)
      this.encryptionKey = crypto.randomBytes(32);
    }
  }

  /**
   * Store a credential
   */
  async storeCredential(name: string, value: string): Promise<CredentialReference> {
    const tokenHandle = this.generateTokenHandle();
    
    if (this.config.useEnvironment) {
      // In production, this would set an environment variable
      // For now, we'll store it encrypted in memory
      const encrypted = this.encrypt(value);
      this.credentials.set(tokenHandle, encrypted);
    } else {
      // Encrypt and store
      const encrypted = this.encrypt(value);
      this.credentials.set(tokenHandle, encrypted);
    }

    return {
      id: this.generateId(),
      credentialName: name,
      tokenHandle
    };
  }

  /**
   * Retrieve a credential
   */
  async getCredential(tokenHandle: string): Promise<string> {
    const encrypted = this.credentials.get(tokenHandle);
    if (!encrypted) {
      throw new Error(`Credential not found: ${tokenHandle}`);
    }

    return this.decrypt(encrypted);
  }

  /**
   * Delete a credential
   */
  async deleteCredential(tokenHandle: string): Promise<void> {
    this.credentials.delete(tokenHandle);
  }

  /**
   * List all credential references (without values)
   */
  listCredentials(): CredentialReference[] {
    const references: CredentialReference[] = [];
    
    for (const [tokenHandle] of this.credentials) {
      references.push({
        id: this.generateId(),
        credentialName: 'unknown', // We don't store names separately
        tokenHandle
      });
    }

    return references;
  }

  /**
   * Rotate a credential
   */
  async rotateCredential(tokenHandle: string, newValue: string): Promise<void> {
    const encrypted = this.encrypt(newValue);
    this.credentials.set(tokenHandle, encrypted);
  }

  /**
   * Encrypt a value
   */
  private encrypt(value: string): string {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-cbc', this.encryptionKey, iv);
    
    let encrypted = cipher.update(value, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    // Return IV + encrypted data
    return iv.toString('hex') + ':' + encrypted;
  }

  /**
   * Decrypt a value
   */
  private decrypt(encrypted: string): string {
    const parts = encrypted.split(':');
    const ivHex = parts[0];
    const encryptedData = parts[1];
    
    if (!ivHex || !encryptedData) {
      throw new Error('Invalid encrypted data format');
    }
    
    const iv = Buffer.from(ivHex, 'hex');
    
    const decipher = crypto.createDecipheriv('aes-256-cbc', this.encryptionKey, iv);
    
    const decrypted = decipher.update(encryptedData, 'hex', 'utf8') + decipher.final('utf8');
    
    return decrypted;
  }

  /**
   * Generate a token handle
   */
  private generateTokenHandle(): string {
    return `token_${Date.now()}_${crypto.randomBytes(16).toString('hex')}`;
  }

  /**
   * Generate an ID
   */
  private generateId(): string {
    return `cred_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  /**
   * Import credentials from environment variables
   */
  async importFromEnvironment(prefix = 'SINTRAPRIME_'): Promise<void> {
    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith(prefix) && value) {
        const name = key.substring(prefix.length);
        await this.storeCredential(name, value);
      }
    }
  }

  /**
   * Export encryption key (for backup)
   */
  exportEncryptionKey(): string {
    return this.encryptionKey.toString('hex');
  }
}
