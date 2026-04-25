import { apiRequest } from './client';
import { Account, Transaction, CreditScore, BudgetCategory } from '@store/financialStore';

export interface FundingOpportunity {
  id: string;
  name: string;
  provider: string;
  type: 'grant' | 'loan' | 'sba' | 'investor' | 'crowdfunding';
  amount: { min: number; max: number };
  interestRate?: number;
  requirements: string[];
  deadline?: string;
  matchScore: number;
  description: string;
}

export const financialAPI = {
  getAccounts: () =>
    apiRequest<Account[]>('get', '/financial/accounts'),

  linkAccount: (publicToken: string) =>
    apiRequest<Account[]>('post', '/financial/accounts/link', { publicToken }),

  unlinkAccount: (accountId: string) =>
    apiRequest<void>('delete', `/financial/accounts/${accountId}`),

  getTransactions: (params?: {
    accountId?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
  }) =>
    apiRequest<Transaction[]>('get', '/financial/transactions', undefined, { params }),

  getCreditScore: () =>
    apiRequest<CreditScore>('get', '/financial/credit-score'),

  getBudget: () =>
    apiRequest<BudgetCategory[]>('get', '/financial/budget'),

  updateBudget: (categoryId: string, budgeted: number) =>
    apiRequest<BudgetCategory>('patch', `/financial/budget/${categoryId}`, { budgeted }),

  getNetWorth: () =>
    apiRequest<{ netWorth: number; assets: number; liabilities: number }>('get', '/financial/net-worth'),

  searchFunding: (params?: { type?: string; minAmount?: number; maxAmount?: number }) =>
    apiRequest<FundingOpportunity[]>('get', '/financial/funding', undefined, { params }),

  getInsights: () =>
    apiRequest<{ insights: string[]; alerts: string[] }>('get', '/financial/insights'),
};
