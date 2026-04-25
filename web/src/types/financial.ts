// Financial Types for SintraPrime-Unified

export type AccountType = 
  | 'checking'
  | 'savings'
  | 'investment'
  | 'retirement'
  | 'credit'
  | 'loan'
  | 'mortgage'
  | 'business';

export type FundingType =
  | 'grant'
  | 'loan'
  | 'sba'
  | 'venture_capital'
  | 'angel'
  | 'crowdfunding'
  | 'cdfi'
  | 'minority_business'
  | 'women_owned'
  | 'veteran_owned'
  | 'government'
  | 'nonprofit';

export type InvestmentType =
  | 'stocks'
  | 'bonds'
  | 'real_estate'
  | 'crypto'
  | 'etf'
  | 'mutual_fund'
  | 'alternative'
  | 'commodities'
  | 'private_equity';

export interface BankAccount {
  id: string;
  institutionName: string;
  institutionLogo?: string;
  accountName: string;
  accountType: AccountType;
  accountNumber: string; // masked
  balance: number;
  availableBalance?: number;
  currency: string;
  lastSynced: string;
  isConnected: boolean;
  plaidItemId?: string;
  transactions?: Transaction[];
}

export interface Transaction {
  id: string;
  accountId: string;
  date: string;
  description: string;
  amount: number;
  category: string;
  subcategory?: string;
  merchant?: string;
  isRecurring: boolean;
  pending: boolean;
  tags: string[];
}

export interface CreditScore {
  score: number;
  bureau: 'equifax' | 'experian' | 'transunion';
  asOfDate: string;
  previousScore?: number;
  change?: number;
  factors: CreditFactor[];
  history: CreditScoreHistory[];
}

export interface CreditFactor {
  name: string;
  impact: 'positive' | 'negative' | 'neutral';
  description: string;
  weight: number;
}

export interface CreditScoreHistory {
  date: string;
  score: number;
  bureau: string;
}

export interface NetWorthEntry {
  date: string;
  totalAssets: number;
  totalLiabilities: number;
  netWorth: number;
  breakdown: {
    cash: number;
    investments: number;
    realEstate: number;
    vehicles: number;
    other: number;
  };
}

export interface Budget {
  id: string;
  month: string;
  year: number;
  income: BudgetCategory[];
  expenses: BudgetCategory[];
  totalIncome: number;
  totalExpenses: number;
  savings: number;
  savingsRate: number;
}

export interface BudgetCategory {
  name: string;
  budgeted: number;
  actual: number;
  variance: number;
  subcategories?: BudgetCategory[];
}

export interface FundingOpportunity {
  id: string;
  name: string;
  provider: string;
  type: FundingType;
  amount: {
    min: number;
    max: number;
  };
  deadline?: string;
  description: string;
  requirements: string[];
  eligibility: string[];
  applicationUrl?: string;
  interestRate?: number;
  termYears?: number;
  isGrant: boolean;
  matchRequired?: number;
  industries?: string[];
  states?: string[];
  tags: string[];
  status: 'open' | 'closed' | 'coming_soon';
  saved?: boolean;
}

export interface Investment {
  id: string;
  symbol?: string;
  name: string;
  type: InvestmentType;
  quantity: number;
  purchasePrice: number;
  currentPrice: number;
  currentValue: number;
  gainLoss: number;
  gainLossPercent: number;
  allocation: number; // percentage of portfolio
  accountId?: string;
  purchaseDate: string;
}

export interface Debt {
  id: string;
  name: string;
  type: 'credit_card' | 'student_loan' | 'auto' | 'mortgage' | 'personal' | 'business' | 'medical' | 'other';
  balance: number;
  interestRate: number;
  minimumPayment: number;
  targetPayment?: number;
  payoffDate?: string;
  accountId?: string;
  strategy: 'avalanche' | 'snowball' | 'consolidation';
  priority: number;
}

export interface DebtPayoffProjection {
  debtId: string;
  name: string;
  currentBalance: number;
  monthlyPayment: number;
  payoffMonths: number;
  totalInterestPaid: number;
  payoffDate: string;
  monthly: Array<{ month: string; balance: number; interest: number; principal: number }>;
}

export interface FinancialGoal {
  id: string;
  name: string;
  type: 'savings' | 'debt_payoff' | 'investment' | 'emergency_fund' | 'retirement' | 'purchase';
  targetAmount: number;
  currentAmount: number;
  progress: number;
  deadline?: string;
  monthlyContribution: number;
  onTrack: boolean;
}

export interface PortfolioSummary {
  totalValue: number;
  dayChange: number;
  dayChangePercent: number;
  totalGainLoss: number;
  totalGainLossPercent: number;
  investments: Investment[];
  allocation: Array<{ type: InvestmentType; value: number; percentage: number }>;
  performance: Array<{ date: string; value: number }>;
}
