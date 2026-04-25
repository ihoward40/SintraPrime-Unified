/**
 * Google Drive Connector - Interact with Google Drive API
 * 
 * Provides safe access to Google Drive for file operations
 */

import { Connector } from '../types/index.js';

export interface GoogleDriveConfig {
  accessToken: string;
  refreshToken?: string;
  clientId?: string;
  clientSecret?: string;
}

export class GoogleDriveConnector implements Connector {
  name = 'google_drive';
  type = 'storage';
  
  private config: GoogleDriveConfig;
  private authenticated = false;
  private baseUrl = 'https://www.googleapis.com/drive/v3';
  private uploadUrl = 'https://www.googleapis.com/upload/drive/v3';

  constructor(config: GoogleDriveConfig) {
    this.config = config;
  }

  /**
   * Authenticate with Google Drive
   */
  async authenticate(): Promise<void> {
    // Verify credentials by fetching about info
    try {
      await this.call('GET', '/about', { fields: 'user' });
      this.authenticated = true;
    } catch (error) {
      throw new Error(`Google Drive authentication failed: ${error}`);
    }
  }

  /**
   * Make an API call to Google Drive
   */
  async call(method: string, endpoint: string, args: any): Promise<any> {
    if (!this.authenticated && endpoint !== '/about') {
      throw new Error('Not authenticated. Call authenticate() first.');
    }

    const url = new URL(`${this.baseUrl}${endpoint}`);
    
    // Add query parameters for GET requests
    if (method === 'GET' && args) {
      Object.entries(args).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    try {
      const response = await fetch(url.toString(), {
        method,
        headers: {
          'Authorization': `Bearer ${this.config.accessToken}`,
          'Content-Type': 'application/json'
        },
        body: method !== 'GET' ? JSON.stringify(args) : undefined
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`Google Drive API error: ${JSON.stringify(error)}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Google Drive API call failed: ${error}`);
    }
  }

  /**
   * List files
   */
  async listFiles(query?: string, pageSize = 100): Promise<any> {
    const params: any = {
      pageSize,
      fields: 'files(id,name,mimeType,createdTime,modifiedTime,size)'
    };
    
    if (query) {
      params.q = query;
    }

    return this.call('GET', '/files', params);
  }

  /**
   * Get file metadata
   */
  async getFile(fileId: string): Promise<any> {
    return this.call('GET', `/files/${fileId}`, {
      fields: 'id,name,mimeType,createdTime,modifiedTime,size,webViewLink'
    });
  }

  /**
   * Download file content
   */
  async downloadFile(fileId: string): Promise<any> {
    const url = `${this.baseUrl}/files/${fileId}?alt=media`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Upload a file
   */
  async uploadFile(fileName: string, content: any, mimeType: string, parentFolderId?: string): Promise<any> {
    const metadata = {
      name: fileName,
      mimeType,
      parents: parentFolderId ? [parentFolderId] : undefined
    };

    const form = new FormData();
    form.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));
    form.append('file', content);

    const response = await fetch(`${this.uploadUrl}/files?uploadType=multipart`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`
      },
      body: form
    });

    if (!response.ok) {
      throw new Error(`Failed to upload file: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Create a folder
   */
  async createFolder(folderName: string, parentFolderId?: string): Promise<any> {
    const metadata = {
      name: folderName,
      mimeType: 'application/vnd.google-apps.folder',
      parents: parentFolderId ? [parentFolderId] : undefined
    };

    return this.call('POST', '/files', metadata);
  }

  /**
   * Delete a file
   */
  async deleteFile(fileId: string): Promise<void> {
    await this.call('DELETE', `/files/${fileId}`, {});
  }

  /**
   * Share a file
   */
  async shareFile(fileId: string, email: string, role: 'reader' | 'writer' | 'commenter'): Promise<any> {
    const permission = {
      type: 'user',
      role,
      emailAddress: email
    };

    const url = `${this.baseUrl}/files/${fileId}/permissions`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.config.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(permission)
    });

    if (!response.ok) {
      throw new Error(`Failed to share file: ${response.statusText}`);
    }

    return response.json();
  }
}
