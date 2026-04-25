// Governance & Entity Types for SintraPrime-Unified

export type EntityType = 
  | 'llc'
  | 'corporation'
  | 'trust'
  | 'partnership'
  | 'sole_proprietorship'
  | 'nonprofit'
  | 'foundation'
  | 'land_trust'
  | 'business_trust'
  | 'statutory_trust';

export type EntityStatus = 'active' | 'dissolved' | 'pending' | 'suspended' | 'inactive';

export type FilingType = 
  | 'annual_report'
  | 'biennial_report'
  | 'amendment'
  | 'dissolution'
  | 'reinstatement'
  | 'foreign_qualification'
  | 'registered_agent_change';

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  status: EntityStatus;
  formationDate: string;
  dissolutionDate?: string;
  state: string;
  registeredAgent: RegisteredAgent;
  ein?: string;
  officers: Officer[];
  members?: Member[];
  assets: EntityAsset[];
  subsidiaries: string[]; // entity IDs
  parentId?: string;
  filings: EntityFiling[];
  complianceItems: ComplianceItem[];
  documents: string[];
  notes?: string;
}

export interface RegisteredAgent {
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  phone?: string;
  email?: string;
}

export interface Officer {
  id: string;
  name: string;
  title: string;
  startDate: string;
  endDate?: string;
  ownership?: number; // percentage
  address?: string;
}

export interface Member {
  id: string;
  name: string;
  ownershipPercent: number;
  memberSince: string;
  votingRights: boolean;
  capitalContribution?: number;
}

export interface EntityAsset {
  id: string;
  entityId: string;
  name: string;
  type: 'real_estate' | 'vehicle' | 'bank_account' | 'investment' | 'business_interest' | 'intellectual_property' | 'other';
  value: number;
  acquisitionDate: string;
  description?: string;
  documents?: string[];
}

export interface EntityFiling {
  id: string;
  entityId: string;
  type: FilingType;
  filedDate: string;
  dueDate?: string;
  status: 'pending' | 'filed' | 'overdue' | 'waived';
  cost?: number;
  confirmationNumber?: string;
  documents?: string[];
}

export interface ComplianceItem {
  id: string;
  entityId: string;
  name: string;
  description: string;
  dueDate: string;
  recurring: boolean;
  frequency?: 'annual' | 'biennial' | 'quarterly' | 'monthly';
  status: 'pending' | 'completed' | 'overdue' | 'not_applicable';
  cost?: number;
  reminderDays: number;
  documents?: string[];
}

export interface AIParliamentSession {
  id: string;
  topic: string;
  startedAt: string;
  endedAt?: string;
  status: 'active' | 'completed' | 'adjourned';
  question: string;
  decision?: string;
  reasoning?: string;
  agents: AIAgent[];
  votes: AgentVote[];
  transcript: DebateMessage[];
  confidence: number;
  humanOverride?: boolean;
  humanDecision?: string;
}

export interface AIAgent {
  id: string;
  name: string;
  role: string;
  specialty: string;
  avatar: string;
  color: string;
  currentPosition?: string;
  confidence?: number;
  votesTotal: number;
  correctVotes: number;
}

export interface AgentVote {
  agentId: string;
  vote: 'yes' | 'no' | 'abstain' | 'defer';
  reasoning: string;
  confidence: number;
  timestamp: string;
}

export interface DebateMessage {
  id: string;
  agentId: string;
  content: string;
  timestamp: string;
  type: 'argument' | 'rebuttal' | 'evidence' | 'question' | 'closing';
  references?: string[];
}

export interface EstateTimeline {
  id: string;
  title: string;
  date: string;
  type: 'formation' | 'transfer' | 'amendment' | 'distribution' | 'death' | 'probate' | 'settlement' | 'tax_event';
  entityId?: string;
  assetId?: string;
  description: string;
  documents?: string[];
  completed: boolean;
  amount?: number;
}

export interface AssetProtectionStrategy {
  id: string;
  name: string;
  description: string;
  entities: string[];
  assets: string[];
  level: 'basic' | 'intermediate' | 'advanced';
  jurisdiction: string[];
  benefits: string[];
  risks: string[];
  implementationSteps: string[];
  estimatedCost: number;
  legalBasis: string[];
}
