import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  BankAccount,
  CreditScore,
  NetWorthEntry,
  Budget,
  FundingOpportunity,
  PortfolioSummary,
  Debt,
  FinancialGoal,
} from '../types/financial';

interface FinancialState {
  accounts: BankAccount[];
  creditScores: CreditScore[];
  netWorthHistory: NetWorthEntry[];
  budget: Budget | null;
  fundingOpportunities: FundingOpportunity[];
  portfolio: PortfolioSummary | null;
  debts: Debt[];
  goals: FinancialGoal[];
  fundingFilter: { type?: string; minAmount?: number; maxAmount?: number; state?: string };
  isLoading: boolean;

  // Actions
  setAccounts: (accounts: BankAccount[]) => void;
  setCreditScores: (scores: CreditScore[]) => void;
  setNetWorthHistory: (history: NetWorthEntry[]) => void;
  setBudget: (budget: Budget) => void;
  setFundingOpportunities: (opportunities: FundingOpportunity[]) => void;
  toggleSaveFunding: (id: string) => void;
  setPortfolio: (portfolio: PortfolioSummary) => void;
  setDebts: (debts: Debt[]) => void;
  setGoals: (goals: FinancialGoal[]) => void;
  setFundingFilter: (filter: Partial<FinancialState['fundingFilter']>) => void;
  setLoading: (loading: boolean) => void;
}

// Mock data generators
const generateNetWorthHistory = (): NetWorthEntry[] => {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const now = new Date();
  return months.slice(0, now.getMonth() + 1).map((month, idx) => {
    const base = 850000 + idx * 18000 + Math.random() * 10000;
    const assets = base + 200000;
    const liabilities = 200000 - idx * 5000;
    return {
      date: `2024-${String(idx + 1).padStart(2, '0')}-01`,
      totalAssets: assets,
      totalLiabilities: Math.max(50000, liabilities),
      netWorth: assets - Math.max(50000, liabilities),
      breakdown: {
        cash: base * 0.15,
        investments: base * 0.35,
        realEstate: base * 0.38,
        vehicles: base * 0.07,
        other: base * 0.05,
      },
    };
  });
};

const mockFundingOpportunities: FundingOpportunity[] = [
  {
    id: 'fund-001',
    name: 'SBA 7(a) Small Business Loan',
    provider: 'Small Business Administration',
    type: 'sba',
    amount: { min: 5000, max: 5000000 },
    description: 'The SBA 7(a) loan program is the SBA\'s primary program for helping small businesses with financing.',
    requirements: ['2+ years in business', 'Good credit score', 'US-based business'],
    eligibility: ['Small business as defined by SBA', 'For-profit business', 'Reasonable invested equity'],
    applicationUrl: 'https://www.sba.gov/funding-programs/loans/7a-loans',
    interestRate: 8.5,
    termYears: 25,
    isGrant: false,
    tags: ['federal', 'loan', 'small business'],
    status: 'open',
    saved: false,
  },
  {
    id: 'fund-002',
    name: 'Minority Business Development Agency Grant',
    provider: 'MBDA',
    type: 'minority_business',
    amount: { min: 50000, max: 500000 },
    deadline: '2024-09-30',
    description: 'Grants to minority-owned businesses for expansion and capacity building.',
    requirements: ['51%+ minority ownership', 'Revenue under $5M', 'Business plan required'],
    eligibility: ['African American', 'Hispanic', 'Asian American', 'Native American owned'],
    isGrant: true,
    tags: ['minority', 'grant', 'expansion'],
    status: 'open',
    saved: true,
  },
  {
    id: 'fund-003',
    name: 'CDFI Small Business Capital Initiative',
    provider: 'Treasury CDFI Fund',
    type: 'cdfi',
    amount: { min: 10000, max: 250000 },
    description: 'Capital access for small businesses in low-income communities.',
    requirements: ['Located in low-income community', 'Under 50 employees', 'Cannot access conventional financing'],
    eligibility: ['Small businesses in LMI communities', 'Startups eligible'],
    interestRate: 5.5,
    termYears: 10,
    isGrant: false,
    tags: ['community', 'low-income', 'accessible'],
    status: 'open',
    saved: false,
  },
  {
    id: 'fund-004',
    name: 'Women-Owned Small Business Federal Contract Program',
    provider: 'SBA',
    type: 'women_owned',
    amount: { min: 100000, max: 8000000 },
    description: 'Federal contracting program for women-owned small businesses.',
    requirements: ['51%+ women-owned', 'SBA certification', 'Applicable industry'],
    eligibility: ['Women-owned businesses', 'Economically disadvantaged WOSB'],
    isGrant: false,
    tags: ['women-owned', 'federal contracts', 'certification'],
    status: 'open',
    saved: false,
  },
  {
    id: 'fund-005',
    name: 'Veteran Business Fund',
    provider: 'SBA Veterans Advantage',
    type: 'veteran_owned',
    amount: { min: 0, max: 350000 },
    description: 'No-fee or reduced-fee SBA loans for veteran entrepreneurs.',
    requirements: ['Honorable discharge', 'Veteran-owned business'],
    eligibility: ['Veterans', 'Service-disabled veterans', 'Military spouses'],
    interestRate: 6.25,
    termYears: 10,
    isGrant: false,
    tags: ['veteran', 'military', 'no-fee loan'],
    status: 'open',
    saved: false,
  },
];

const mockDebts: Debt[] = [
  {
    id: 'debt-001',
    name: 'Business Line of Credit',
    type: 'business',
    balance: 45000,
    interestRate: 12.5,
    minimumPayment: 1125,
    targetPayment: 3000,
    strategy: 'avalanche',
    priority: 1,
  },
  {
    id: 'debt-002',
    name: 'Law School Student Loans',
    type: 'student_loan',
    balance: 128000,
    interestRate: 6.8,
    minimumPayment: 1470,
    targetPayment: 2000,
    strategy: 'avalanche',
    priority: 2,
  },
  {
    id: 'debt-003',
    name: 'Office Mortgage',
    type: 'mortgage',
    balance: 380000,
    interestRate: 4.5,
    minimumPayment: 2100,
    targetPayment: 2100,
    strategy: 'snowball',
    priority: 3,
  },
];

export const useFinancialStore = create<FinancialState>()(
  devtools(
    (set) => ({
      accounts: [
        { id: 'acc-001', institutionName: 'Chase Bank', accountName: 'Business Checking', accountType: 'checking', accountNumber: '****4821', balance: 127450.23, availableBalance: 127450.23, currency: 'USD', lastSynced: new Date().toISOString(), isConnected: true },
        { id: 'acc-002', institutionName: 'Chase Bank', accountName: 'Personal Savings', accountType: 'savings', accountNumber: '****9234', balance: 84320.00, availableBalance: 84320.00, currency: 'USD', lastSynced: new Date().toISOString(), isConnected: true },
        { id: 'acc-003', institutionName: 'Fidelity', accountName: 'Investment Portfolio', accountType: 'investment', accountNumber: '****7744', balance: 342180.50, currency: 'USD', lastSynced: new Date().toISOString(), isConnected: true },
        { id: 'acc-004', institutionName: 'Vanguard', accountName: 'Roth IRA', accountType: 'retirement', accountNumber: '****3392', balance: 198450.75, currency: 'USD', lastSynced: new Date().toISOString(), isConnected: true },
        { id: 'acc-005', institutionName: 'Amex', accountName: 'Business Platinum Card', accountType: 'credit', accountNumber: '****8811', balance: -4820.33, availableBalance: 95179.67, currency: 'USD', lastSynced: new Date().toISOString(), isConnected: true },
      ],
      creditScores: [
        {
          score: 742,
          bureau: 'experian',
          asOfDate: new Date().toISOString(),
          previousScore: 730,
          change: 12,
          factors: [
            { name: 'Payment History', impact: 'positive', description: '100% on-time payments', weight: 35 },
            { name: 'Credit Utilization', impact: 'positive', description: 'Low utilization at 8%', weight: 30 },
            { name: 'Credit Age', impact: 'neutral', description: 'Average account age 6 years', weight: 15 },
            { name: 'Credit Mix', impact: 'positive', description: 'Diverse mix of credit types', weight: 10 },
            { name: 'New Credit', impact: 'negative', description: '2 hard inquiries in last year', weight: 10 },
          ],
          history: Array.from({ length: 12 }, (_, i) => ({
            date: `2024-${String(i + 1).padStart(2, '0')}-01`,
            score: 700 + i * 3 + Math.floor(Math.random() * 5),
            bureau: 'experian',
          })),
        },
      ],
      netWorthHistory: generateNetWorthHistory(),
      budget: null,
      fundingOpportunities: mockFundingOpportunities,
      portfolio: null,
      debts: mockDebts,
      goals: [
        { id: 'goal-001', name: 'Emergency Fund', type: 'emergency_fund', targetAmount: 50000, currentAmount: 84320, progress: 100, monthlyContribution: 0, onTrack: true },
        { id: 'goal-002', name: 'Pay Off Student Loans', type: 'debt_payoff', targetAmount: 128000, currentAmount: 42000, progress: 32.8, deadline: '2027-01-01', monthlyContribution: 2000, onTrack: true },
        { id: 'goal-003', name: 'Investment Portfolio Target', type: 'investment', targetAmount: 500000, currentAmount: 342180, progress: 68.4, deadline: '2026-12-31', monthlyContribution: 5000, onTrack: true },
        { id: 'goal-004', name: 'Second Property Purchase', type: 'purchase', targetAmount: 150000, currentAmount: 47500, progress: 31.7, deadline: '2025-12-01', monthlyContribution: 3500, onTrack: false },
      ],
      fundingFilter: {},
      isLoading: false,

      setAccounts: (accounts) => set({ accounts }),
      setCreditScores: (creditScores) => set({ creditScores }),
      setNetWorthHistory: (netWorthHistory) => set({ netWorthHistory }),
      setBudget: (budget) => set({ budget }),
      setFundingOpportunities: (fundingOpportunities) => set({ fundingOpportunities }),
      toggleSaveFunding: (id) =>
        set((state) => ({
          fundingOpportunities: state.fundingOpportunities.map((f) =>
            f.id === id ? { ...f, saved: !f.saved } : f
          ),
        })),
      setPortfolio: (portfolio) => set({ portfolio }),
      setDebts: (debts) => set({ debts }),
      setGoals: (goals) => set({ goals }),
      setFundingFilter: (filter) =>
        set((state) => ({ fundingFilter: { ...state.fundingFilter, ...filter } })),
      setLoading: (isLoading) => set({ isLoading }),
    }),
    { name: 'SintraPrime FinancialStore' }
  )
);
