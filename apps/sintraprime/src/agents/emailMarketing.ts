/**
 * Email Marketing Automation Module for SintraPrime
 * 
 * Autonomous email marketing inspired by Manus AI:
 * - Automated email sequence creation
 * - Subscriber segmentation
 * - A/B testing for subject lines and content
 * - Performance tracking and optimization
 * - Integration with Klaviyo, Mailchimp, and other ESPs
 * 
 * @module EmailMarketing
 */

import { Task, TaskResult, ExecutionContext } from '../types/index.js';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface EmailSequence {
  id: string;
  name: string;
  type: SequenceType;
  status: 'draft' | 'active' | 'paused' | 'completed';
  trigger: SequenceTrigger;
  emails: SequenceEmail[];
  settings: SequenceSettings;
  metrics: SequenceMetrics;
  createdAt: Date;
  updatedAt: Date;
}

export type SequenceType = 
  | 'welcome'
  | 'abandoned_cart'
  | 'post_purchase'
  | 'win_back'
  | 'browse_abandonment'
  | 'product_launch'
  | 'promotional'
  | 'educational'
  | 'custom';

export interface SequenceTrigger {
  type: 'event' | 'segment' | 'date' | 'manual';
  event?: string;
  segmentId?: string;
  date?: Date;
  conditions?: TriggerCondition[];
}

export interface TriggerCondition {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than';
  value: any;
}

export interface SequenceEmail {
  id: string;
  name: string;
  position: number;
  delay: EmailDelay;
  subject: string;
  preheader?: string;
  content: EmailContent;
  variants?: EmailVariant[];
  conditions?: EmailCondition[];
  metrics: EmailMetrics;
}

export interface EmailDelay {
  value: number;
  unit: 'minutes' | 'hours' | 'days' | 'weeks';
}

export interface EmailContent {
  type: 'html' | 'template';
  html?: string;
  templateId?: string;
  templateData?: Record<string, any>;
  blocks?: ContentBlock[];
}

export interface ContentBlock {
  type: 'text' | 'image' | 'button' | 'product' | 'divider' | 'social';
  content: Record<string, any>;
}

export interface EmailVariant {
  id: string;
  name: string;
  subject?: string;
  content?: EmailContent;
  weight: number;
  metrics: EmailMetrics;
}

export interface EmailCondition {
  type: 'if' | 'unless';
  field: string;
  operator: string;
  value: any;
  action: 'skip' | 'send' | 'branch';
  branchEmailId?: string;
}

export interface SequenceSettings {
  sendingWindow?: {
    startHour: number;
    endHour: number;
    timezone: string;
    daysOfWeek: number[];
  };
  throttling?: {
    maxPerHour: number;
    maxPerDay: number;
  };
  unsubscribeHandling: 'remove' | 'pause' | 'continue';
  doubleOptIn: boolean;
}

export interface SequenceMetrics {
  totalSent: number;
  totalDelivered: number;
  totalOpened: number;
  totalClicked: number;
  totalConverted: number;
  totalUnsubscribed: number;
  totalBounced: number;
  totalSpamReports: number;
  openRate: number;
  clickRate: number;
  conversionRate: number;
  unsubscribeRate: number;
  revenue: number;
}

export interface EmailMetrics {
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  converted: number;
  unsubscribed: number;
  bounced: number;
  spamReports: number;
  openRate: number;
  clickRate: number;
  conversionRate: number;
}

export interface Subscriber {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  status: 'subscribed' | 'unsubscribed' | 'bounced' | 'complained';
  source: string;
  tags: string[];
  segments: string[];
  customFields: Record<string, any>;
  activityHistory: SubscriberActivity[];
  createdAt: Date;
  updatedAt: Date;
}

export interface SubscriberActivity {
  type: 'subscribed' | 'opened' | 'clicked' | 'purchased' | 'unsubscribed';
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface Segment {
  id: string;
  name: string;
  type: 'static' | 'dynamic';
  conditions?: SegmentCondition[];
  subscriberIds?: string[];
  subscriberCount: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface SegmentCondition {
  field: string;
  operator: string;
  value: any;
  conjunction?: 'and' | 'or';
}

export interface EmailTemplate {
  id: string;
  name: string;
  category: string;
  html: string;
  variables: string[];
  thumbnail?: string;
}

// ============================================================================
// EMAIL SEQUENCE BUILDER
// ============================================================================

export class EmailSequenceBuilder {
  private context: ExecutionContext;
  
  constructor(context: ExecutionContext) {
    this.context = context;
  }
  
  /**
   * Creates a welcome sequence
   */
  createWelcomeSequence(params: {
    brandName: string;
    discountCode?: string;
    discountPercent?: number;
  }): EmailSequence {
    const emails: SequenceEmail[] = [
      {
        id: 'welcome_1',
        name: 'Welcome Email',
        position: 1,
        delay: { value: 0, unit: 'minutes' },
        subject: `Welcome to ${params.brandName}! 🎉`,
        preheader: params.discountCode 
          ? `Your ${params.discountPercent}% discount is inside`
          : 'Thanks for joining us',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: `Hi {{first_name|default:"there"}},\n\nWelcome to ${params.brandName}! We're thrilled to have you.`
              }
            },
            ...(params.discountCode ? [{
              type: 'text' as const,
              content: {
                text: `As a thank you for joining, here's ${params.discountPercent}% off your first order:\n\n**${params.discountCode}**`
              }
            }] : []),
            {
              type: 'button',
              content: {
                text: 'Shop Now',
                url: '{{shop_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'welcome_2',
        name: 'Brand Story',
        position: 2,
        delay: { value: 2, unit: 'days' },
        subject: `The story behind ${params.brandName}`,
        preheader: 'Learn more about who we are',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: `Hi {{first_name|default:"there"}},\n\nWe wanted to share a bit about why we started ${params.brandName}...`
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'welcome_3',
        name: 'Best Sellers',
        position: 3,
        delay: { value: 4, unit: 'days' },
        subject: 'Our customers\' favorites 💝',
        preheader: 'See what everyone is loving',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nHere are our most-loved products:'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{best_sellers}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      }
    ];
    
    return {
      id: `seq_welcome_${Date.now()}`,
      name: 'Welcome Series',
      type: 'welcome',
      status: 'draft',
      trigger: {
        type: 'event',
        event: 'subscriber.created'
      },
      emails,
      settings: {
        unsubscribeHandling: 'remove',
        doubleOptIn: false
      },
      metrics: this.initializeSequenceMetrics(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
  
  /**
   * Creates an abandoned cart sequence
   */
  createAbandonedCartSequence(params: {
    brandName: string;
    discountCode?: string;
    discountPercent?: number;
  }): EmailSequence {
    const emails: SequenceEmail[] = [
      {
        id: 'cart_1',
        name: 'Cart Reminder',
        position: 1,
        delay: { value: 1, unit: 'hours' },
        subject: 'You left something behind...',
        preheader: 'Your cart is waiting for you',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nLooks like you left some items in your cart. Don\'t worry, we saved them for you!'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{cart_items}}'
              }
            },
            {
              type: 'button',
              content: {
                text: 'Complete Your Order',
                url: '{{checkout_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'cart_2',
        name: 'Cart Reminder 2',
        position: 2,
        delay: { value: 24, unit: 'hours' },
        subject: 'Still thinking it over?',
        preheader: 'Your items are selling fast',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nJust a friendly reminder that your cart is still waiting. These items are popular and might sell out soon!'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{cart_items}}'
              }
            },
            {
              type: 'button',
              content: {
                text: 'Return to Cart',
                url: '{{checkout_url}}'
              }
            }
          ]
        },
        conditions: [
          {
            type: 'unless',
            field: 'has_purchased',
            operator: 'equals',
            value: true,
            action: 'skip'
          }
        ],
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'cart_3',
        name: 'Final Reminder with Discount',
        position: 3,
        delay: { value: 48, unit: 'hours' },
        subject: params.discountCode 
          ? `${params.discountPercent}% off to complete your order! 🎁`
          : 'Last chance to grab your items!',
        preheader: params.discountCode
          ? 'Special discount just for you'
          : 'Don\'t miss out',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: params.discountCode
                  ? `Hi {{first_name|default:"there"}},\n\nWe really want you to have these items! Here's ${params.discountPercent}% off:\n\n**${params.discountCode}**`
                  : 'Hi {{first_name|default:"there"}},\n\nThis is your last reminder! Your cart items won\'t be reserved much longer.'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{cart_items}}'
              }
            },
            {
              type: 'button',
              content: {
                text: 'Complete Purchase',
                url: '{{checkout_url}}'
              }
            }
          ]
        },
        conditions: [
          {
            type: 'unless',
            field: 'has_purchased',
            operator: 'equals',
            value: true,
            action: 'skip'
          }
        ],
        metrics: this.initializeEmailMetrics()
      }
    ];
    
    return {
      id: `seq_cart_${Date.now()}`,
      name: 'Abandoned Cart Recovery',
      type: 'abandoned_cart',
      status: 'draft',
      trigger: {
        type: 'event',
        event: 'checkout.abandoned'
      },
      emails,
      settings: {
        unsubscribeHandling: 'remove',
        doubleOptIn: false
      },
      metrics: this.initializeSequenceMetrics(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
  
  /**
   * Creates a post-purchase sequence
   */
  createPostPurchaseSequence(params: {
    brandName: string;
    reviewPlatform?: string;
  }): EmailSequence {
    const emails: SequenceEmail[] = [
      {
        id: 'post_1',
        name: 'Order Confirmation',
        position: 1,
        delay: { value: 0, unit: 'minutes' },
        subject: 'Order Confirmed! 🎉 #{{order_number}}',
        preheader: 'Thanks for your purchase',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nThank you for your order! We\'re getting it ready for you.'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{order_items}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'post_2',
        name: 'Shipping Notification',
        position: 2,
        delay: { value: 0, unit: 'minutes' },
        subject: 'Your order is on its way! 📦',
        preheader: 'Track your shipment',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Great news! Your order has shipped.\n\nTracking number: {{tracking_number}}'
              }
            },
            {
              type: 'button',
              content: {
                text: 'Track Order',
                url: '{{tracking_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'post_3',
        name: 'Review Request',
        position: 3,
        delay: { value: 7, unit: 'days' },
        subject: 'How are you enjoying your purchase?',
        preheader: 'We\'d love your feedback',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nWe hope you\'re loving your new items! Would you mind leaving a quick review? It helps other customers and means the world to us.'
              }
            },
            {
              type: 'button',
              content: {
                text: 'Leave a Review',
                url: params.reviewPlatform || '{{review_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'post_4',
        name: 'Cross-sell',
        position: 4,
        delay: { value: 14, unit: 'days' },
        subject: 'You might also like these...',
        preheader: 'Personalized recommendations',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: 'Hi {{first_name|default:"there"}},\n\nBased on your recent purchase, we thought you might like these:'
              }
            },
            {
              type: 'product',
              content: {
                productIds: '{{recommended_products}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      }
    ];
    
    return {
      id: `seq_post_${Date.now()}`,
      name: 'Post-Purchase Series',
      type: 'post_purchase',
      status: 'draft',
      trigger: {
        type: 'event',
        event: 'order.placed'
      },
      emails,
      settings: {
        unsubscribeHandling: 'remove',
        doubleOptIn: false
      },
      metrics: this.initializeSequenceMetrics(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
  
  /**
   * Creates a win-back sequence for inactive customers
   */
  createWinBackSequence(params: {
    brandName: string;
    discountCode: string;
    discountPercent: number;
    inactiveDays: number;
  }): EmailSequence {
    const emails: SequenceEmail[] = [
      {
        id: 'winback_1',
        name: 'We Miss You',
        position: 1,
        delay: { value: 0, unit: 'minutes' },
        subject: 'We miss you! 💔',
        preheader: 'It\'s been a while',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: `Hi {{first_name|default:"there"}},\n\nIt's been ${params.inactiveDays} days since your last visit. We miss you!`
              }
            },
            {
              type: 'button',
              content: {
                text: 'See What\'s New',
                url: '{{shop_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'winback_2',
        name: 'Special Offer',
        position: 2,
        delay: { value: 3, unit: 'days' },
        subject: `${params.discountPercent}% off just for you! 🎁`,
        preheader: 'A special discount to welcome you back',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: `Hi {{first_name|default:"there"}},\n\nWe'd love to have you back! Here's ${params.discountPercent}% off your next order:\n\n**${params.discountCode}**`
              }
            },
            {
              type: 'button',
              content: {
                text: 'Shop Now',
                url: '{{shop_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      },
      {
        id: 'winback_3',
        name: 'Last Chance',
        position: 3,
        delay: { value: 7, unit: 'days' },
        subject: 'Last chance for your discount!',
        preheader: 'Your offer expires soon',
        content: {
          type: 'html',
          blocks: [
            {
              type: 'text',
              content: {
                text: `Hi {{first_name|default:"there"}},\n\nYour ${params.discountPercent}% discount expires soon! Don't miss out.\n\n**${params.discountCode}**`
              }
            },
            {
              type: 'button',
              content: {
                text: 'Use My Discount',
                url: '{{shop_url}}'
              }
            }
          ]
        },
        metrics: this.initializeEmailMetrics()
      }
    ];
    
    return {
      id: `seq_winback_${Date.now()}`,
      name: 'Win-Back Series',
      type: 'win_back',
      status: 'draft',
      trigger: {
        type: 'segment',
        segmentId: 'inactive_customers',
        conditions: [
          {
            field: 'last_purchase_date',
            operator: 'less_than',
            value: `${params.inactiveDays}_days_ago`
          }
        ]
      },
      emails,
      settings: {
        unsubscribeHandling: 'remove',
        doubleOptIn: false
      },
      metrics: this.initializeSequenceMetrics(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
  
  private initializeEmailMetrics(): EmailMetrics {
    return {
      sent: 0,
      delivered: 0,
      opened: 0,
      clicked: 0,
      converted: 0,
      unsubscribed: 0,
      bounced: 0,
      spamReports: 0,
      openRate: 0,
      clickRate: 0,
      conversionRate: 0
    };
  }
  
  private initializeSequenceMetrics(): SequenceMetrics {
    return {
      totalSent: 0,
      totalDelivered: 0,
      totalOpened: 0,
      totalClicked: 0,
      totalConverted: 0,
      totalUnsubscribed: 0,
      totalBounced: 0,
      totalSpamReports: 0,
      openRate: 0,
      clickRate: 0,
      conversionRate: 0,
      unsubscribeRate: 0,
      revenue: 0
    };
  }
}

// ============================================================================
// EMAIL MARKETING MANAGER
// ============================================================================

export class EmailMarketingManager {
  private context: ExecutionContext;
  private sequenceBuilder: EmailSequenceBuilder;
  private sequences: Map<string, EmailSequence> = new Map();
  private subscribers: Map<string, Subscriber> = new Map();
  private segments: Map<string, Segment> = new Map();
  private espProvider: 'klaviyo' | 'mailchimp' | 'sendgrid' | null = null;
  private apiKey: string = '';
  
  constructor(context: ExecutionContext) {
    this.context = context;
    this.sequenceBuilder = new EmailSequenceBuilder(context);
  }
  
  /**
   * Configures the ESP (Email Service Provider)
   */
  configureESP(provider: 'klaviyo' | 'mailchimp' | 'sendgrid', apiKey: string): void {
    this.espProvider = provider;
    this.apiKey = apiKey;
  }
  
  /**
   * Sets up all essential email sequences for e-commerce
   */
  async setupEcommerceSequences(params: {
    brandName: string;
    welcomeDiscount?: { code: string; percent: number };
    cartDiscount?: { code: string; percent: number };
    winBackDiscount?: { code: string; percent: number };
  }): Promise<TaskResult> {
    try {
      const sequences: EmailSequence[] = [];
      
      // Welcome sequence
      const welcome = this.sequenceBuilder.createWelcomeSequence({
        brandName: params.brandName,
        discountCode: params.welcomeDiscount?.code,
        discountPercent: params.welcomeDiscount?.percent
      });
      sequences.push(welcome);
      this.sequences.set(welcome.id, welcome);
      
      // Abandoned cart sequence
      const cart = this.sequenceBuilder.createAbandonedCartSequence({
        brandName: params.brandName,
        discountCode: params.cartDiscount?.code,
        discountPercent: params.cartDiscount?.percent
      });
      sequences.push(cart);
      this.sequences.set(cart.id, cart);
      
      // Post-purchase sequence
      const postPurchase = this.sequenceBuilder.createPostPurchaseSequence({
        brandName: params.brandName
      });
      sequences.push(postPurchase);
      this.sequences.set(postPurchase.id, postPurchase);
      
      // Win-back sequence
      if (params.winBackDiscount) {
        const winBack = this.sequenceBuilder.createWinBackSequence({
          brandName: params.brandName,
          discountCode: params.winBackDiscount.code,
          discountPercent: params.winBackDiscount.percent,
          inactiveDays: 60
        });
        sequences.push(winBack);
        this.sequences.set(winBack.id, winBack);
      }
      
      // Sync to ESP if configured
      if (this.espProvider) {
        for (const sequence of sequences) {
          await this.syncSequenceToESP(sequence);
        }
      }
      
      return {
        success: true,
        output: {
          sequencesCreated: sequences.length,
          sequences: sequences.map(s => ({
            id: s.id,
            name: s.name,
            type: s.type,
            emailCount: s.emails.length
          })),
          message: 'E-commerce email sequences created successfully'
        }
      };
    } catch (error) {
      return {
        success: false,
        error: `Failed to setup sequences: ${error}`
      };
    }
  }
  
  /**
   * Syncs a sequence to the configured ESP
   */
  private async syncSequenceToESP(sequence: EmailSequence): Promise<void> {
    switch (this.espProvider) {
      case 'klaviyo':
        await this.syncToKlaviyo(sequence);
        break;
      case 'mailchimp':
        await this.syncToMailchimp(sequence);
        break;
      case 'sendgrid':
        await this.syncToSendgrid(sequence);
        break;
    }
  }
  
  private async syncToKlaviyo(sequence: EmailSequence): Promise<void> {
    // POST https://a.klaviyo.com/api/flows/
    // In production, would make actual API calls
  }
  
  private async syncToMailchimp(sequence: EmailSequence): Promise<void> {
    // POST https://us1.api.mailchimp.com/3.0/automations
  }
  
  private async syncToSendgrid(sequence: EmailSequence): Promise<void> {
    // POST https://api.sendgrid.com/v3/marketing/automations
  }
  
  /**
   * Generates performance report for all sequences
   */
  async generatePerformanceReport(): Promise<{
    overview: {
      totalSubscribers: number;
      activeSequences: number;
      totalEmailsSent: number;
      overallOpenRate: number;
      overallClickRate: number;
      totalRevenue: number;
    };
    sequencePerformance: {
      sequenceId: string;
      sequenceName: string;
      metrics: SequenceMetrics;
    }[];
    recommendations: string[];
  }> {
    let totalSent = 0;
    let totalOpened = 0;
    let totalClicked = 0;
    let totalRevenue = 0;
    
    const sequencePerformance: any[] = [];
    
    for (const [_, sequence] of this.sequences) {
      totalSent += sequence.metrics.totalSent;
      totalOpened += sequence.metrics.totalOpened;
      totalClicked += sequence.metrics.totalClicked;
      totalRevenue += sequence.metrics.revenue;
      
      sequencePerformance.push({
        sequenceId: sequence.id,
        sequenceName: sequence.name,
        metrics: sequence.metrics
      });
    }
    
    const recommendations = this.generateRecommendations(sequencePerformance);
    
    return {
      overview: {
        totalSubscribers: this.subscribers.size,
        activeSequences: Array.from(this.sequences.values())
          .filter(s => s.status === 'active').length,
        totalEmailsSent: totalSent,
        overallOpenRate: totalSent > 0 ? (totalOpened / totalSent) * 100 : 0,
        overallClickRate: totalOpened > 0 ? (totalClicked / totalOpened) * 100 : 0,
        totalRevenue
      },
      sequencePerformance,
      recommendations
    };
  }
  
  /**
   * Generates recommendations based on performance
   */
  private generateRecommendations(performance: any[]): string[] {
    const recommendations: string[] = [];
    
    for (const seq of performance) {
      if (seq.metrics.openRate < 20) {
        recommendations.push(
          `${seq.sequenceName}: Low open rate (${seq.metrics.openRate.toFixed(1)}%). Test new subject lines.`
        );
      }
      
      if (seq.metrics.clickRate < 2) {
        recommendations.push(
          `${seq.sequenceName}: Low click rate (${seq.metrics.clickRate.toFixed(1)}%). Improve CTAs and content.`
        );
      }
      
      if (seq.metrics.unsubscribeRate > 1) {
        recommendations.push(
          `${seq.sequenceName}: High unsubscribe rate (${seq.metrics.unsubscribeRate.toFixed(1)}%). Review frequency and content relevance.`
        );
      }
    }
    
    return recommendations;
  }
  
  /**
   * Activates a sequence
   */
  async activateSequence(sequenceId: string): Promise<TaskResult> {
    const sequence = this.sequences.get(sequenceId);
    if (!sequence) {
      return { success: false, error: 'Sequence not found' };
    }
    
    sequence.status = 'active';
    sequence.updatedAt = new Date();
    
    return {
      success: true,
      output: { message: `Sequence "${sequence.name}" is now active` }
    };
  }
  
  /**
   * Gets all sequences
   */
  getSequences(): EmailSequence[] {
    return Array.from(this.sequences.values());
  }
}

export default EmailMarketingManager;
