import api from './client';
import type {
  BankAccount,
  CreditScore,
  NetWorthEntry,
  Budget,
  FundingOpportunity,
  PortfolioSummary,
  Debt,
  DebtPayoffProjection,
  FinancialGoal,
} from '../types/financial';

export const financialAPI = {
  // Accounts
  getAccounts: () =>
    api.get<BankAccount[]>('/financial/accounts'),

  getAccount: (id: string) =>
    api.get<BankAccount>(`/financial/accounts/${id}`),

  linkPlaid: (publicToken: string) =>
    api.post<{ success: boolean; accountsAdded: number }>('/financial/plaid/exchange', { publicToken }),

  syncAccounts: () =>
    api.post<{ synced: number; lastSync: string }>('/financial/accounts/sync'),

  // Credit Score
  getCreditScore: () =>
    api.get<CreditScore[]>('/financial/credit'),

  refreshCreditScore: () =>
    api.post<CreditScore>('/financial/credit/refresh'),

  // Net Worth
  getNetWorthHistory: (months?: number) =>
    api.get<NetWorthEntry[]>('/financial/networth', months ? { months } : undefined),

  // Budget
  getBudget: (month: number, year: number) =>
    api.get<Budget>(`/financial/budget/${year}/${month}`),

  updateBudget: (month: number, year: number, data: Partial<Budget>) =>
    api.patch<Budget>(`/financial/budget/${year}/${month}`, data),

  // Funding Opportunities
  getFundingOpportunities: (params?: {
    type?: string;
    minAmount?: number;
    maxAmount?: number;
    state?: string;
    industry?: string;
  }) =>
    api.get<FundingOpportunity[]>('/financial/funding', params as Record<string, unknown>),

  saveFunding: (id: string) =>
    api.post<void>(`/financial/funding/${id}/save`),

  // Portfolio
  getPortfolio: () =>
    api.get<PortfolioSummary>('/financial/portfolio'),

  // Debt
  getDebts: () =>
    api.get<Debt[]>('/financial/debts'),

  getDebtProjection: (debtId: string, extraPayment?: number) =>
    api.get<DebtPayoffProjection>(`/financial/debts/${debtId}/projection`, extraPayment ? { extraPayment } : undefined),

  // Goals
  getGoals: () =>
    api.get<FinancialGoal[]>('/financial/goals'),

  createGoal: (data: Partial<FinancialGoal>) =>
    api.post<FinancialGoal>('/financial/goals', data),

  updateGoal: (id: string, data: Partial<FinancialGoal>) =>
    api.patch<FinancialGoal>(`/financial/goals/${id}`, data),
};
