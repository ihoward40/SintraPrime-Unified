/**
 * Ad Campaign Manager for SintraPrime
 * 
 * Autonomous ad campaign management inspired by Manus AI:
 * - Creates and manages Facebook/Meta ad campaigns
 * - Automatic budget optimization
 * - A/B testing automation
 * - Daily performance reporting
 * - Autonomous scaling of winning ads
 * 
 * @module AdCampaignManager
 */

import { Task, TaskResult, ExecutionContext } from '../types/index.js';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface AdCampaign {
  id: string;
  name: string;
  platform: 'facebook' | 'google' | 'tiktok' | 'pinterest';
  objective: CampaignObjective;
  status: 'draft' | 'active' | 'paused' | 'completed';
  budget: CampaignBudget;
  targeting: AudienceTargeting;
  adSets: AdSet[];
  createdAt: Date;
  updatedAt: Date;
  metrics: CampaignMetrics;
}

export type CampaignObjective = 
  | 'awareness'
  | 'traffic'
  | 'engagement'
  | 'leads'
  | 'sales'
  | 'conversions';

export interface CampaignBudget {
  type: 'daily' | 'lifetime';
  amount: number;
  currency: string;
  spent: number;
  remaining: number;
}

export interface AudienceTargeting {
  locations: string[];
  ageRange: { min: number; max: number };
  genders: ('male' | 'female' | 'all')[];
  interests: string[];
  behaviors: string[];
  customAudiences: string[];
  lookalikeAudiences: string[];
  excludedAudiences: string[];
}

export interface AdSet {
  id: string;
  name: string;
  status: 'active' | 'paused';
  budget: number;
  bidStrategy: BidStrategy;
  placements: Placement[];
  ads: Ad[];
  metrics: AdSetMetrics;
}

export type BidStrategy = 
  | 'lowest_cost'
  | 'cost_cap'
  | 'bid_cap'
  | 'target_cost';

export type Placement = 
  | 'facebook_feed'
  | 'facebook_stories'
  | 'facebook_reels'
  | 'instagram_feed'
  | 'instagram_stories'
  | 'instagram_reels'
  | 'audience_network'
  | 'messenger';

export interface Ad {
  id: string;
  name: string;
  type: 'image' | 'video' | 'carousel' | 'collection';
  status: 'active' | 'paused' | 'rejected';
  creative: AdCreative;
  metrics: AdMetrics;
}

export interface AdCreative {
  headline: string;
  primaryText: string;
  description?: string;
  callToAction: string;
  mediaUrls: string[];
  landingPageUrl: string;
}

export interface CampaignMetrics {
  impressions: number;
  reach: number;
  clicks: number;
  ctr: number;
  cpc: number;
  cpm: number;
  conversions: number;
  conversionRate: number;
  costPerConversion: number;
  roas: number;
  spend: number;
  revenue: number;
}

export interface AdSetMetrics extends CampaignMetrics {
  frequency: number;
}

export interface AdMetrics extends CampaignMetrics {
  engagements: number;
  videoViews?: number;
  videoWatchTime?: number;
}

export interface OptimizationRule {
  id: string;
  name: string;
  condition: OptimizationCondition;
  action: OptimizationAction;
  enabled: boolean;
  cooldownHours: number;
  lastTriggered?: Date;
}

export interface OptimizationCondition {
  metric: keyof CampaignMetrics;
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  value: number;
  timeframe: 'last_24h' | 'last_7d' | 'last_30d' | 'lifetime';
}

export interface OptimizationAction {
  type: 'pause' | 'resume' | 'scale_up' | 'scale_down' | 'duplicate' | 'alert';
  params?: Record<string, any>;
}

export interface DailyReport {
  date: string;
  campaigns: CampaignSummary[];
  totalSpend: number;
  totalRevenue: number;
  overallRoas: number;
  topPerformers: Ad[];
  underperformers: Ad[];
  recommendations: string[];
  alerts: Alert[];
}

export interface CampaignSummary {
  campaignId: string;
  campaignName: string;
  spend: number;
  revenue: number;
  roas: number;
  conversions: number;
  trend: 'up' | 'down' | 'stable';
}

export interface Alert {
  severity: 'info' | 'warning' | 'critical';
  message: string;
  campaignId?: string;
  adId?: string;
  recommendedAction?: string;
}

// ============================================================================
// AD CAMPAIGN MANAGER
// ============================================================================

export class AdCampaignManager {
  private context: ExecutionContext;
  private campaigns: Map<string, AdCampaign> = new Map();
  private optimizationRules: OptimizationRule[] = [];
  private metaAccessToken: string = '';
  private adAccountId: string = '';
  
  constructor(context: ExecutionContext) {
    this.context = context;
    this.initializeDefaultRules();
  }
  
  /**
   * Configures Meta (Facebook) API credentials
   */
  configureMetaApi(accessToken: string, adAccountId: string): void {
    this.metaAccessToken = accessToken;
    this.adAccountId = adAccountId;
  }
  
  /**
   * Initializes default optimization rules
   */
  private initializeDefaultRules(): void {
    this.optimizationRules = [
      // Pause underperforming ads
      {
        id: 'pause_low_roas',
        name: 'Pause Low ROAS Ads',
        condition: {
          metric: 'roas',
          operator: '<',
          value: 1.5,
          timeframe: 'last_7d'
        },
        action: { type: 'pause' },
        enabled: true,
        cooldownHours: 24
      },
      // Scale winning ads
      {
        id: 'scale_high_roas',
        name: 'Scale High ROAS Ads',
        condition: {
          metric: 'roas',
          operator: '>',
          value: 3.0,
          timeframe: 'last_7d'
        },
        action: { 
          type: 'scale_up',
          params: { percentage: 20 }
        },
        enabled: true,
        cooldownHours: 48
      },
      // Alert on high CPC
      {
        id: 'alert_high_cpc',
        name: 'Alert High CPC',
        condition: {
          metric: 'cpc',
          operator: '>',
          value: 2.0,
          timeframe: 'last_24h'
        },
        action: { 
          type: 'alert',
          params: { severity: 'warning' }
        },
        enabled: true,
        cooldownHours: 12
      },
      // Pause high spend low conversion
      {
        id: 'pause_no_conversions',
        name: 'Pause No Conversion Ads',
        condition: {
          metric: 'conversions',
          operator: '==',
          value: 0,
          timeframe: 'last_7d'
        },
        action: { type: 'pause' },
        enabled: true,
        cooldownHours: 24
      }
    ];
  }
  
  /**
   * Creates a new ad campaign
   */
  async createCampaign(params: {
    name: string;
    platform: 'facebook' | 'google' | 'tiktok';
    objective: CampaignObjective;
    dailyBudget: number;
    targeting: AudienceTargeting;
    creatives: AdCreative[];
  }): Promise<TaskResult> {
    try {
      const campaignId = `camp_${Date.now()}`;
      
      // Create ad sets with A/B testing variations
      const adSets = this.createAdSetsWithVariations(params.creatives, params.targeting);
      
      const campaign: AdCampaign = {
        id: campaignId,
        name: params.name,
        platform: params.platform,
        objective: params.objective,
        status: 'draft',
        budget: {
          type: 'daily',
          amount: params.dailyBudget,
          currency: 'USD',
          spent: 0,
          remaining: params.dailyBudget
        },
        targeting: params.targeting,
        adSets,
        createdAt: new Date(),
        updatedAt: new Date(),
        metrics: this.initializeMetrics()
      };
      
      this.campaigns.set(campaignId, campaign);
      
      // If Meta API is configured, create campaign via API
      if (this.metaAccessToken && params.platform === 'facebook') {
        await this.createMetaCampaign(campaign);
      }
      
      return {
        success: true,
        output: {
          campaignId,
          adSetsCreated: adSets.length,
          totalAds: adSets.reduce((sum, set) => sum + set.ads.length, 0),
          status: 'draft',
          message: 'Campaign created successfully. Review and activate when ready.'
        }
      };
    } catch (error) {
      return {
        success: false,
        error: `Failed to create campaign: ${error}`
      };
    }
  }
  
  /**
   * Creates ad sets with A/B testing variations
   */
  private createAdSetsWithVariations(
    creatives: AdCreative[],
    targeting: AudienceTargeting
  ): AdSet[] {
    const adSets: AdSet[] = [];
    
    // Create interest-based ad sets
    const interestGroups = this.groupInterests(targeting.interests);
    
    interestGroups.forEach((interests, index) => {
      const adSet: AdSet = {
        id: `adset_${Date.now()}_${index}`,
        name: `Interest Group ${index + 1}`,
        status: 'active',
        budget: 0, // Will be set by campaign budget optimization
        bidStrategy: 'lowest_cost',
        placements: ['facebook_feed', 'instagram_feed', 'instagram_stories'],
        ads: creatives.map((creative, creativeIndex) => ({
          id: `ad_${Date.now()}_${index}_${creativeIndex}`,
          name: `Ad ${creativeIndex + 1}`,
          type: creative.mediaUrls.length > 1 ? 'carousel' : 'image',
          status: 'active',
          creative,
          metrics: this.initializeMetrics() as AdMetrics
        })),
        metrics: this.initializeMetrics() as AdSetMetrics
      };
      
      adSets.push(adSet);
    });
    
    return adSets;
  }
  
  /**
   * Groups interests for A/B testing
   */
  private groupInterests(interests: string[]): string[][] {
    const groupSize = Math.ceil(interests.length / 3);
    const groups: string[][] = [];
    
    for (let i = 0; i < interests.length; i += groupSize) {
      groups.push(interests.slice(i, i + groupSize));
    }
    
    return groups.length > 0 ? groups : [interests];
  }
  
  /**
   * Creates campaign via Meta Marketing API
   */
  private async createMetaCampaign(campaign: AdCampaign): Promise<void> {
    // In production, this would make actual API calls:
    // POST https://graph.facebook.com/v18.0/act_{ad_account_id}/campaigns
    
    const campaignPayload = {
      name: campaign.name,
      objective: this.mapObjectiveToMeta(campaign.objective),
      status: 'PAUSED',
      special_ad_categories: []
    };
    
    // Create ad sets
    for (const adSet of campaign.adSets) {
      // POST https://graph.facebook.com/v18.0/act_{ad_account_id}/adsets
    }
    
    // Create ads
    for (const adSet of campaign.adSets) {
      for (const ad of adSet.ads) {
        // POST https://graph.facebook.com/v18.0/act_{ad_account_id}/ads
      }
    }
  }
  
  /**
   * Maps internal objective to Meta API objective
   */
  private mapObjectiveToMeta(objective: CampaignObjective): string {
    const mapping: Record<CampaignObjective, string> = {
      awareness: 'OUTCOME_AWARENESS',
      traffic: 'OUTCOME_TRAFFIC',
      engagement: 'OUTCOME_ENGAGEMENT',
      leads: 'OUTCOME_LEADS',
      sales: 'OUTCOME_SALES',
      conversions: 'OUTCOME_SALES'
    };
    return mapping[objective];
  }
  
  /**
   * Runs autonomous optimization on all active campaigns
   */
  async runOptimization(): Promise<{
    actionsApplied: number;
    alerts: Alert[];
    summary: string;
  }> {
    const alerts: Alert[] = [];
    let actionsApplied = 0;
    
    for (const [campaignId, campaign] of this.campaigns) {
      if (campaign.status !== 'active') continue;
      
      // Check each optimization rule
      for (const rule of this.optimizationRules) {
        if (!rule.enabled) continue;
        
        // Check cooldown
        if (rule.lastTriggered) {
          const hoursSinceTriggered = 
            (Date.now() - rule.lastTriggered.getTime()) / (1000 * 60 * 60);
          if (hoursSinceTriggered < rule.cooldownHours) continue;
        }
        
        // Evaluate condition
        const shouldTrigger = this.evaluateCondition(campaign, rule.condition);
        
        if (shouldTrigger) {
          const result = await this.applyAction(campaign, rule.action);
          if (result.applied) {
            actionsApplied++;
            rule.lastTriggered = new Date();
          }
          if (result.alert) {
            alerts.push(result.alert);
          }
        }
      }
      
      // Ad-level optimization
      for (const adSet of campaign.adSets) {
        for (const ad of adSet.ads) {
          const adAlerts = await this.optimizeAd(campaign, adSet, ad);
          alerts.push(...adAlerts);
        }
      }
    }
    
    return {
      actionsApplied,
      alerts,
      summary: `Optimization complete. ${actionsApplied} actions applied, ${alerts.length} alerts generated.`
    };
  }
  
  /**
   * Evaluates an optimization condition
   */
  private evaluateCondition(
    campaign: AdCampaign,
    condition: OptimizationCondition
  ): boolean {
    const metricValue = campaign.metrics[condition.metric];
    
    switch (condition.operator) {
      case '>': return metricValue > condition.value;
      case '<': return metricValue < condition.value;
      case '>=': return metricValue >= condition.value;
      case '<=': return metricValue <= condition.value;
      case '==': return metricValue === condition.value;
      case '!=': return metricValue !== condition.value;
      default: return false;
    }
  }
  
  /**
   * Applies an optimization action
   */
  private async applyAction(
    campaign: AdCampaign,
    action: OptimizationAction
  ): Promise<{ applied: boolean; alert?: Alert }> {
    switch (action.type) {
      case 'pause':
        campaign.status = 'paused';
        return { 
          applied: true,
          alert: {
            severity: 'info',
            message: `Campaign "${campaign.name}" paused due to optimization rule`,
            campaignId: campaign.id
          }
        };
        
      case 'scale_up':
        const scaleUpPercent = action.params?.percentage || 20;
        campaign.budget.amount *= (1 + scaleUpPercent / 100);
        return {
          applied: true,
          alert: {
            severity: 'info',
            message: `Campaign "${campaign.name}" budget increased by ${scaleUpPercent}%`,
            campaignId: campaign.id
          }
        };
        
      case 'scale_down':
        const scaleDownPercent = action.params?.percentage || 20;
        campaign.budget.amount *= (1 - scaleDownPercent / 100);
        return {
          applied: true,
          alert: {
            severity: 'info',
            message: `Campaign "${campaign.name}" budget decreased by ${scaleDownPercent}%`,
            campaignId: campaign.id
          }
        };
        
      case 'alert':
        return {
          applied: false,
          alert: {
            severity: action.params?.severity || 'warning',
            message: `Alert triggered for campaign "${campaign.name}"`,
            campaignId: campaign.id
          }
        };
        
      default:
        return { applied: false };
    }
  }
  
  /**
   * Optimizes individual ad performance
   */
  private async optimizeAd(
    campaign: AdCampaign,
    adSet: AdSet,
    ad: Ad
  ): Promise<Alert[]> {
    const alerts: Alert[] = [];
    
    // Check for ad fatigue (high frequency, declining CTR)
    if (adSet.metrics.frequency > 3 && ad.metrics.ctr < 1) {
      alerts.push({
        severity: 'warning',
        message: `Ad "${ad.name}" showing signs of fatigue. Consider refreshing creative.`,
        campaignId: campaign.id,
        adId: ad.id,
        recommendedAction: 'Create new ad variations'
      });
    }
    
    // Check for rejected ads
    if (ad.status === 'rejected') {
      alerts.push({
        severity: 'critical',
        message: `Ad "${ad.name}" was rejected. Review and fix policy violations.`,
        campaignId: campaign.id,
        adId: ad.id,
        recommendedAction: 'Review ad creative for policy compliance'
      });
    }
    
    return alerts;
  }
  
  /**
   * Generates daily performance report
   */
  async generateDailyReport(): Promise<DailyReport> {
    const today = new Date().toISOString().split('T')[0] ?? '';
    const campaignSummaries: CampaignSummary[] = [];
    let totalSpend = 0;
    let totalRevenue = 0;
    const topPerformers: Ad[] = [];
    const underperformers: Ad[] = [];
    const alerts: Alert[] = [];
    
    for (const [_, campaign] of this.campaigns) {
      if (campaign.status !== 'active') continue;
      
      const summary: CampaignSummary = {
        campaignId: campaign.id,
        campaignName: campaign.name,
        spend: campaign.metrics.spend,
        revenue: campaign.metrics.revenue,
        roas: campaign.metrics.roas,
        conversions: campaign.metrics.conversions,
        trend: this.calculateTrend(campaign)
      };
      
      campaignSummaries.push(summary);
      totalSpend += campaign.metrics.spend;
      totalRevenue += campaign.metrics.revenue;
      
      // Identify top and under performers
      for (const adSet of campaign.adSets) {
        for (const ad of adSet.ads) {
          if (ad.metrics.roas > 3) {
            topPerformers.push(ad);
          } else if (ad.metrics.roas < 1 && ad.metrics.spend > 50) {
            underperformers.push(ad);
          }
        }
      }
    }
    
    // Generate recommendations
    const recommendations = this.generateRecommendations(
      campaignSummaries,
      topPerformers,
      underperformers
    );
    
    return {
      date: today,
      campaigns: campaignSummaries,
      totalSpend,
      totalRevenue,
      overallRoas: totalSpend > 0 ? totalRevenue / totalSpend : 0,
      topPerformers: topPerformers.slice(0, 5),
      underperformers: underperformers.slice(0, 5),
      recommendations,
      alerts
    };
  }
  
  /**
   * Calculates performance trend
   */
  private calculateTrend(campaign: AdCampaign): 'up' | 'down' | 'stable' {
    // In production, would compare with historical data
    if (campaign.metrics.roas > 2.5) return 'up';
    if (campaign.metrics.roas < 1.5) return 'down';
    return 'stable';
  }
  
  /**
   * Generates actionable recommendations
   */
  private generateRecommendations(
    summaries: CampaignSummary[],
    topPerformers: Ad[],
    underperformers: Ad[]
  ): string[] {
    const recommendations: string[] = [];
    
    if (topPerformers.length > 0) {
      recommendations.push(
        `Scale budget for top ${topPerformers.length} performing ads by 20-30%`
      );
      recommendations.push(
        'Create lookalike audiences from top performer conversions'
      );
    }
    
    if (underperformers.length > 0) {
      recommendations.push(
        `Review and pause ${underperformers.length} underperforming ads`
      );
      recommendations.push(
        'Test new creative variations for underperforming ad sets'
      );
    }
    
    const lowRoasCampaigns = summaries.filter(s => s.roas < 1.5);
    if (lowRoasCampaigns.length > 0) {
      recommendations.push(
        `${lowRoasCampaigns.length} campaigns have ROAS below 1.5x - consider audience refinement`
      );
    }
    
    return recommendations;
  }
  
  /**
   * Initializes empty metrics object
   */
  private initializeMetrics(): CampaignMetrics {
    return {
      impressions: 0,
      reach: 0,
      clicks: 0,
      ctr: 0,
      cpc: 0,
      cpm: 0,
      conversions: 0,
      conversionRate: 0,
      costPerConversion: 0,
      roas: 0,
      spend: 0,
      revenue: 0
    };
  }
  
  /**
   * Adds a custom optimization rule
   */
  addOptimizationRule(rule: OptimizationRule): void {
    this.optimizationRules.push(rule);
  }
  
  /**
   * Gets all campaigns
   */
  getCampaigns(): AdCampaign[] {
    return Array.from(this.campaigns.values());
  }
  
  /**
   * Activates a campaign
   */
  async activateCampaign(campaignId: string): Promise<TaskResult> {
    const campaign = this.campaigns.get(campaignId);
    if (!campaign) {
      return { success: false, error: 'Campaign not found' };
    }
    
    campaign.status = 'active';
    campaign.updatedAt = new Date();
    
    return {
      success: true,
      output: { message: `Campaign "${campaign.name}" is now active` }
    };
  }
  
  /**
   * Pauses a campaign
   */
  async pauseCampaign(campaignId: string): Promise<TaskResult> {
    const campaign = this.campaigns.get(campaignId);
    if (!campaign) {
      return { success: false, error: 'Campaign not found' };
    }
    
    campaign.status = 'paused';
    campaign.updatedAt = new Date();
    
    return {
      success: true,
      output: { message: `Campaign "${campaign.name}" has been paused` }
    };
  }
}

export default AdCampaignManager;
