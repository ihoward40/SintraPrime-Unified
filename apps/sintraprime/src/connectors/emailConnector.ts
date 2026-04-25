/**
 * Email Connector - Send and manage emails
 * 
 * Supports Gmail API and generic SMTP
 */

import { Connector } from '../types/index.js';

export interface EmailConfig {
  type: 'gmail' | 'smtp';
  // Gmail config
  accessToken?: string;
  // SMTP config
  host?: string;
  port?: number;
  secure?: boolean;
  user?: string;
  password?: string;
}

export class EmailConnector implements Connector {
  name = 'email';
  type = 'communication';
  
  private config: EmailConfig;
  private authenticated = false;

  constructor(config: EmailConfig) {
    this.config = config;
  }

  /**
   * Authenticate
   */
  async authenticate(): Promise<void> {
    if (this.config.type === 'gmail') {
      await this.authenticateGmail();
    } else {
      await this.authenticateSMTP();
    }
    this.authenticated = true;
  }

  /**
   * Authenticate with Gmail
   */
  private async authenticateGmail(): Promise<void> {
    try {
      const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/profile', {
        headers: {
          'Authorization': `Bearer ${this.config.accessToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Gmail authentication failed');
      }
    } catch (error) {
      throw new Error(`Gmail authentication failed: ${error}`);
    }
  }

  /**
   * Authenticate with SMTP (test connection)
   */
  private async authenticateSMTP(): Promise<void> {
    // In a real implementation, this would test the SMTP connection
    // For now, we'll just validate the config
    if (!this.config.host || !this.config.user || !this.config.password) {
      throw new Error('SMTP configuration incomplete');
    }
  }

  /**
   * Make an API call
   */
  async call(method: string, args: any): Promise<any> {
    if (!this.authenticated) {
      throw new Error('Not authenticated. Call authenticate() first.');
    }

    if (method === 'send') {
      return this.sendEmail(args);
    } else if (method === 'list') {
      return this.listEmails(args);
    } else {
      throw new Error(`Unknown method: ${method}`);
    }
  }

  /**
   * Send an email
   */
  async sendEmail(email: {
    to: string | string[];
    cc?: string | string[];
    bcc?: string | string[];
    subject: string;
    body: string;
    html?: string;
    attachments?: any[];
  }): Promise<any> {
    if (this.config.type === 'gmail') {
      return this.sendGmailEmail(email);
    } else {
      return this.sendSMTPEmail(email);
    }
  }

  /**
   * Send email via Gmail API
   */
  private async sendGmailEmail(email: any): Promise<any> {
    // Create the email message in RFC 2822 format
    const to = Array.isArray(email.to) ? email.to.join(',') : email.to;
    const message = [
      `To: ${to}`,
      email.cc ? `Cc: ${Array.isArray(email.cc) ? email.cc.join(',') : email.cc}` : '',
      `Subject: ${email.subject}`,
      'Content-Type: text/html; charset=utf-8',
      '',
      email.html || email.body
    ].filter(Boolean).join('\n');

    // Encode the message in base64url format
    const encodedMessage = btoa(message).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

    const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ raw: encodedMessage })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to send email: ${JSON.stringify(error)}`);
    }

    return response.json();
  }

  /**
   * Send email via SMTP
   */
  private async sendSMTPEmail(email: any): Promise<any> {
    // In a real implementation, this would use nodemailer or similar
    // For now, this is a placeholder
    throw new Error('SMTP sending not yet implemented. Use Gmail API or implement nodemailer integration.');
  }

  /**
   * List emails
   */
  async listEmails(options: {
    maxResults?: number;
    query?: string;
  } = {}): Promise<any> {
    if (this.config.type !== 'gmail') {
      throw new Error('List emails is only supported for Gmail');
    }

    const params = new URLSearchParams({
      maxResults: String(options.maxResults || 10)
    });

    if (options.query) {
      params.append('q', options.query);
    }

    const response = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me/messages?${params}`, {
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to list emails');
    }

    return response.json();
  }

  /**
   * Get email by ID
   */
  async getEmail(messageId: string): Promise<any> {
    if (this.config.type !== 'gmail') {
      throw new Error('Get email is only supported for Gmail');
    }

    const response = await fetch(`https://gmail.googleapis.com/gmail/v1/users/me/messages/${messageId}`, {
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to get email');
    }

    return response.json();
  }
}
