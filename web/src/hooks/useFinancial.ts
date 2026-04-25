import { useFinancialStore } from '../store/financialStore';

export function useFinancial() {
  const store = useFinancialStore();

  const totalAssets = store.accounts
    .filter((a) => a.balance > 0)
    .reduce((sum, a) => sum + a.balance, 0);

  const totalLiabilities = store.accounts
    .filter((a) => a.balance < 0)
    .reduce((sum, a) => sum + Math.abs(a.balance), 0) +
    store.debts.reduce((sum, d) => sum + d.balance, 0);

  const netWorth = totalAssets - totalLiabilities;

  const currentMonthNetWorth = store.netWorthHistory[store.netWorthHistory.length - 1];
  const previousMonthNetWorth = store.netWorthHistory[store.netWorthHistory.length - 2];
  const netWorthChange = currentMonthNetWorth && previousMonthNetWorth
    ? currentMonthNetWorth.netWorth - previousMonthNetWorth.netWorth
    : 0;
  const netWorthChangePercent = previousMonthNetWorth
    ? (netWorthChange / previousMonthNetWorth.netWorth) * 100
    : 0;

  const primaryCreditScore = store.creditScores[0]?.score ?? 0;

  const filteredFunding = store.fundingOpportunities.filter((f) => {
    const { type, minAmount, maxAmount, state } = store.fundingFilter;
    if (type && f.type !== type) return false;
    if (minAmount && f.amount.max < minAmount) return false;
    if (maxAmount && f.amount.min > maxAmount) return false;
    if (state && f.states && !f.states.includes(state)) return false;
    return true;
  });

  const totalDebt = store.debts.reduce((sum, d) => sum + d.balance, 0);
  const monthlyDebtPayment = store.debts.reduce((sum, d) => sum + d.minimumPayment, 0);

  return {
    ...store,
    totalAssets,
    totalLiabilities,
    netWorth,
    netWorthChange,
    netWorthChangePercent,
    primaryCreditScore,
    filteredFunding,
    totalDebt,
    monthlyDebtPayment,
  };
}
