// Legal Types for SintraPrime-Unified

export type CaseStatus = 
  | 'intake' 
  | 'research' 
  | 'drafting' 
  | 'filing' 
  | 'monitoring' 
  | 'closed'
  | 'settlement'
  | 'appeal';

export type CasePriority = 'low' | 'medium' | 'high' | 'critical';

export type PracticeArea = 
  | 'civil_rights'
  | 'criminal_defense'
  | 'constitutional'
  | 'contract'
  | 'tort'
  | 'property'
  | 'family'
  | 'estate'
  | 'trust'
  | 'tax'
  | 'corporate'
  | 'securities'
  | 'bankruptcy'
  | 'immigration'
  | 'ip'
  | 'employment'
  | 'environmental'
  | 'administrative'
  | 'international'
  | 'ucc';

export type CourtLevel = 
  | 'federal_supreme'
  | 'federal_circuit'
  | 'federal_district'
  | 'federal_bankruptcy'
  | 'state_supreme'
  | 'state_appellate'
  | 'state_trial'
  | 'state_probate'
  | 'administrative';

export type MotionType =
  | 'motion_to_dismiss'
  | 'summary_judgment'
  | 'preliminary_injunction'
  | 'temporary_restraining_order'
  | 'motion_in_limine'
  | 'habeas_corpus'
  | 'mandamus'
  | 'certiorari'
  | 'declaratory_judgment'
  | 'default_judgment'
  | 'reconsideration'
  | 'new_trial'
  | 'compel_discovery'
  | 'protective_order'
  | 'sanctions';

export interface Party {
  id: string;
  name: string;
  role: 'plaintiff' | 'defendant' | 'petitioner' | 'respondent' | 'third_party' | 'intervenor';
  attorney?: string;
  contact?: string;
  address?: string;
}

export interface CourtDate {
  id: string;
  caseId: string;
  date: string;
  time?: string;
  type: 'hearing' | 'trial' | 'deposition' | 'mediation' | 'deadline' | 'status_conference';
  court: string;
  judge?: string;
  notes?: string;
  completed: boolean;
}

export interface Document {
  id: string;
  caseId?: string;
  name: string;
  type: 'motion' | 'brief' | 'order' | 'complaint' | 'answer' | 'discovery' | 'evidence' | 'contract' | 'trust' | 'will' | 'deed' | 'other';
  category: 'legal' | 'financial' | 'estate' | 'trust' | 'corporate' | 'personal';
  uploadedAt: string;
  size: number;
  url?: string;
  tags: string[];
  version: number;
  isConfidential: boolean;
}

export interface Case {
  id: string;
  caseNumber: string;
  title: string;
  description: string;
  status: CaseStatus;
  priority: CasePriority;
  practiceArea: PracticeArea;
  court?: string;
  courtLevel?: CourtLevel;
  judge?: string;
  filingDate: string;
  nextDeadline?: string;
  closedDate?: string;
  parties: Party[];
  documents: Document[];
  courtDates: CourtDate[];
  motions: Motion[];
  assignedAttorney: string;
  estimatedValue?: number;
  settlementAmount?: number;
  tags: string[];
  notes?: string;
  aiAnalysis?: AIAnalysis;
}

export interface Motion {
  id: string;
  caseId: string;
  type: MotionType;
  title: string;
  status: 'draft' | 'filed' | 'pending' | 'granted' | 'denied' | 'under_advisement';
  filedDate?: string;
  dueDate?: string;
  content?: string;
  aiGenerated: boolean;
  attachments: string[];
}

export interface AIAnalysis {
  caseId: string;
  generatedAt: string;
  successProbability: number;
  keyIssues: string[];
  recommendedActions: string[];
  relevantCases: string[];
  riskFactors: string[];
  strategyNotes: string;
}

export interface CaseLaw {
  id: string;
  citation: string;
  title: string;
  court: string;
  year: number;
  jurisdiction: string;
  practiceAreas: PracticeArea[];
  summary: string;
  holding: string;
  fullText?: string;
  relevanceScore?: number;
  citedBy: string[];
  cites: string[];
  tags: string[];
  bookmarked?: boolean;
}

export interface TrustDoctrine {
  id: string;
  name: string;
  description: string;
  jurisdiction: string[];
  uccSection?: string;
  keyCases: string[];
  practicalApplication: string;
  category: 'formation' | 'administration' | 'termination' | 'beneficiary' | 'trustee' | 'asset_protection' | 'tax' | 'ucc';
}

export interface UCCFiling {
  id: string;
  filingNumber: string;
  debtorName: string;
  securedParty: string;
  collateral: string;
  filingDate: string;
  expirationDate: string;
  jurisdiction: string;
  status: 'active' | 'lapsed' | 'terminated' | 'amended';
  amendments: UCCAmendment[];
}

export interface UCCAmendment {
  id: string;
  filingId: string;
  type: 'continuation' | 'termination' | 'assignment' | 'amendment';
  filedDate: string;
  notes?: string;
}

export interface LegalAlert {
  id: string;
  type: 'deadline' | 'new_case_law' | 'filing_required' | 'court_order' | 'settlement_offer';
  title: string;
  description: string;
  caseId?: string;
  dueDate?: string;
  priority: CasePriority;
  read: boolean;
  createdAt: string;
}
