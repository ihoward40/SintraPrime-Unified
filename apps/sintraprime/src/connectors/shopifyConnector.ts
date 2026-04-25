/**
 * Shopify Connector - Interact with Shopify Admin API
 * 
 * Provides safe, rate-limited access to Shopify operations
 */

import { Connector } from '../types/index.js';

export interface ShopifyConfig {
  shop: string; // e.g., 'mystore.myshopify.com'
  accessToken: string;
  apiVersion: string; // e.g., '2024-01'
}

export class ShopifyConnector implements Connector {
  name = 'shopify';
  type = 'ecommerce';
  
  private config: ShopifyConfig;
  private authenticated = false;
  private rateLimitRemaining = 40; // Shopify default: 40 requests per second
  private rateLimitResetTime = Date.now();

  constructor(config: ShopifyConfig) {
    this.config = config;
  }

  /**
   * Authenticate with Shopify
   */
  async authenticate(): Promise<void> {
    // Verify credentials by making a test API call
    try {
      await this.call('GET', '/admin/api/' + this.config.apiVersion + '/shop.json', {});
      this.authenticated = true;
    } catch (error) {
      throw new Error(`Shopify authentication failed: ${error}`);
    }
  }

  /**
   * Make an API call to Shopify
   */
  async call(method: string, endpoint: string, args: any): Promise<any> {
    if (!this.authenticated) {
      throw new Error('Not authenticated. Call authenticate() first.');
    }

    // Rate limiting
    await this.checkRateLimit();

    const url = `https://${this.config.shop}${endpoint}`;
    const headers = {
      'X-Shopify-Access-Token': this.config.accessToken,
      'Content-Type': 'application/json'
    };

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: method !== 'GET' ? JSON.stringify(args) : undefined
      });

      // Update rate limit info from response headers
      this.updateRateLimit(response);

      if (!response.ok) {
        throw new Error(`Shopify API error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Shopify API call failed: ${error}`);
    }
  }

  /**
   * Get products
   */
  async getProducts(limit = 50): Promise<any> {
    return this.call('GET', `/admin/api/${this.config.apiVersion}/products.json?limit=${limit}`, {});
  }

  /**
   * Create a product
   */
  async createProduct(product: any): Promise<any> {
    return this.call('POST', `/admin/api/${this.config.apiVersion}/products.json`, { product });
  }

  /**
   * Update a product
   */
  async updateProduct(productId: string, product: any): Promise<any> {
    return this.call('PUT', `/admin/api/${this.config.apiVersion}/products/${productId}.json`, { product });
  }

  /**
   * Get orders
   */
  async getOrders(limit = 50): Promise<any> {
    return this.call('GET', `/admin/api/${this.config.apiVersion}/orders.json?limit=${limit}`, {});
  }

  /**
   * Get order by ID
   */
  async getOrder(orderId: string): Promise<any> {
    return this.call('GET', `/admin/api/${this.config.apiVersion}/orders/${orderId}.json`, {});
  }

  /**
   * Check rate limit and wait if necessary
   */
  private async checkRateLimit(): Promise<void> {
    if (this.rateLimitRemaining <= 1) {
      const now = Date.now();
      const waitTime = Math.max(0, this.rateLimitResetTime - now);
      if (waitTime > 0) {
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }

  /**
   * Update rate limit info from response headers
   */
  private updateRateLimit(response: Response): void {
    const remaining = response.headers.get('X-Shopify-Shop-Api-Call-Limit');
    if (remaining) {
      const [used, total] = remaining.split('/').map(Number);
      this.rateLimitRemaining = (total ?? 0) - (used ?? 0);
      this.rateLimitResetTime = Date.now() + 1000; // Reset after 1 second
    }
  }
}
