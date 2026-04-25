import { create } from 'zustand';

export interface Account {
  id: string;
  name: string;
  institution: string;
  type: 'checking' | 'savings' | 'investment' | 'credit' | 'loan' | 'crypto';
  balance: number;
  currency: string;
  lastFour?: string;
  interestRate?: number;
  creditLimit?: number;
  logoUrl?: string;
}

export interface Transaction {
  id: string;
  accountId: string;
  date: string;
  description: string;
  amount: number;
  category: string;
  type: 'credit' | 'debit';
  pending: boolean;
}

export interface CreditScoreFactor {
  name: string;
  score: number;
  maxScore: number;
  impact: 'high' | 'medium' | 'low';
  trend: 'up' | 'down' | 'stable';
}

export interface CreditScore {
  score: number;
  previousScore: number;
  lastUpdated: string;
  bureau: string;
  factors: CreditScoreFactor[];
  history: { month: string; score: number }[];
}

export interface BudgetCategory {
  id: string;
  name: string;
  budgeted: number;
  spent: number;
  color: string;
  icon: string;
}

interface FinancialState {
  accounts: Account[];
  transactions: Transaction[];
  creditScore: CreditScore | null;
  budgetCategories: BudgetCategory[];
  netWorth: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  isLoading: boolean;

  setAccounts: (accounts: Account[]) => void;
  setTransactions: (transactions: Transaction[]) => void;
  setCreditScore: (score: CreditScore) => void;
  setBudgetCategories: (cats: BudgetCategory[]) => void;
  setLoading: (loading: boolean) => void;
  getTotalBalance: () => number;
}

const mockAccounts: Account[] = [
  {
    id: 'acc-001',
    name: 'Chase Total Checking',
    institution: 'Chase',
    type: 'checking',
    balance: 12450.67,
    currency: 'USD',
    lastFour: '4821',
  },
  {
    id: 'acc-002',
    name: 'Marcus High-Yield Savings',
    institution: 'Goldman Sachs',
    type: 'savings',
    balance: 85000.00,
    currency: 'USD',
    interestRate: 5.25,
  },
  {
    id: 'acc-003',
    name: 'Fidelity Investment Portfolio',
    institution: 'Fidelity',
    type: 'investment',
    balance: 342890.12,
    currency: 'USD',
  },
  {
    id: 'acc-004',
    name: 'Amex Platinum',
    institution: 'American Express',
    type: 'credit',
    balance: -4230.18,
    currency: 'USD',
    lastFour: '3097',
    creditLimit: 25000,
  },
];

const mockCreditScore: CreditScore = {
  score: 742,
  previousScore: 728,
  lastUpdated: '2026-04-01',
  bureau: 'Equifax',
  factors: [
    { name: 'Payment History', score: 95, maxScore: 100, impact: 'high', trend: 'stable' },
    { name: 'Credit Utilization', score: 72, maxScore: 100, impact: 'high', trend: 'up' },
    { name: 'Credit Age', score: 68, maxScore: 100, impact: 'medium', trend: 'stable' },
    { name: 'Account Mix', score: 80, maxScore: 100, impact: 'low', trend: 'stable' },
    { name: 'New Credit', score: 88, maxScore: 100, impact: 'low', trend: 'up' },
  ],
  history: [
    { month: 'Nov', score: 710 },
    { month: 'Dec', score: 718 },
    { month: 'Jan', score: 720 },
    { month: 'Feb', score: 728 },
    { month: 'Mar', score: 735 },
    { month: 'Apr', score: 742 },
  ],
};

const mockBudget: BudgetCategory[] = [
  { id: 'b1', name: 'Housing', budgeted: 3500, spent: 3500, color: '#3B82F6', icon: 'home' },
  { id: 'b2', name: 'Food & Dining', budgeted: 1200, spent: 890, color: '#22C55E', icon: 'utensils' },
  { id: 'b3', name: 'Transportation', budgeted: 600, spent: 420, color: '#F59E0B', icon: 'car' },
  { id: 'b4', name: 'Legal Fees', budgeted: 2000, spent: 1500, color: '#D4AF37', icon: 'scale' },
  { id: 'b5', name: 'Entertainment', budgeted: 500, spent: 650, color: '#EF4444', icon: 'film' },
  { id: 'b6', name: 'Healthcare', budgeted: 400, spent: 220, color: '#8B5CF6', icon: 'heart' },
];

export const useFinancialStore = create<FinancialState>((set, get) => ({
  accounts: mockAccounts,
  transactions: [],
  creditScore: mockCreditScore,
  budgetCategories: mockBudget,
  netWorth: 436110.61,
  monthlyIncome: 18500,
  monthlyExpenses: 11180,
  isLoading: false,

  setAccounts: (accounts) => set({ accounts }),
  setTransactions: (transactions) => set({ transactions }),
  setCreditScore: (creditScore) => set({ creditScore }),
  setBudgetCategories: (budgetCategories) => set({ budgetCategories }),
  setLoading: (isLoading) => set({ isLoading }),
  getTotalBalance: () =>
    get().accounts.reduce((sum, acc) => sum + acc.balance, 0),
}));
