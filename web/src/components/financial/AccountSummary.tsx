import { Building2, TrendingUp, TrendingDown } from 'lucide-react';
import Badge from '../ui/Badge';

interface Account {
  id: string;
  name: string;
  institution: string;
  type: 'checking' | 'savings' | 'investment' | 'credit' | 'loan';
  balance: number;
  change?: number;
  last4?: string;
}

const mockAccounts: Account[] = [
  { id: 'a1', name: 'Primary Checking', institution: 'Chase Bank', type: 'checking', balance: 24850, change: 1240, last4: '4721' },
  { id: 'a2', name: 'High-Yield Savings', institution: 'Marcus by Goldman', type: 'savings', balance: 85000, change: 420, last4: '8832' },
  { id: 'a3', name: 'Business Checking', institution: 'Chase Bank', type: 'checking', balance: 52340, change: -3200, last4: '2291' },
  { id: 'a4', name: 'Brokerage Account', institution: 'Fidelity', type: 'investment', balance: 218500, change: 8750, last4: '6614' },
  { id: 'a5', name: 'Roth IRA', institution: 'Fidelity', type: 'investment', balance: 81200, change: 3100, last4: '5509' },
  { id: 'a6', name: 'Business Credit Card', institution: 'Amex', type: 'credit', balance: -8420, change: -1500, last4: '3007' },
];

const typeColors: Record<string, string> = {
  checking: 'blue',
  savings: 'green',
  investment: 'gold',
  credit: 'red',
  loan: 'amber',
};

export default function AccountSummary() {
  const totalAssets = mockAccounts.filter(a => a.balance > 0).reduce((s, a) => s + a.balance, 0);
  const totalLiabilities = Math.abs(mockAccounts.filter(a => a.balance < 0).reduce((s, a) => s + a.balance, 0));
  const netWorth = totalAssets - totalLiabilities;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-2.5 bg-slate-800/40 rounded-xl text-center">
          <div className="text-xs text-slate-500 mb-0.5">Assets</div>
          <div className="text-sm font-bold text-emerald-400">${(totalAssets / 1000).toFixed(0)}K</div>
        </div>
        <div className="p-2.5 bg-slate-800/40 rounded-xl text-center">
          <div className="text-xs text-slate-500 mb-0.5">Liabilities</div>
          <div className="text-sm font-bold text-rose-400">${(totalLiabilities / 1000).toFixed(1)}K</div>
        </div>
        <div className="p-2.5 bg-slate-800/40 rounded-xl text-center">
          <div className="text-xs text-slate-500 mb-0.5">Net Worth</div>
          <div className="text-sm font-bold text-gold">${(netWorth / 1000).toFixed(0)}K</div>
        </div>
      </div>

      <div className="space-y-2">
        {mockAccounts.map((account) => (
          <div
            key={account.id}
            className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-800/30 transition-colors"
          >
            <div className="w-8 h-8 rounded-lg bg-slate-800/60 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-4 h-4 text-slate-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-medium text-slate-200 truncate">{account.name}</p>
                <Badge variant={typeColors[account.type] as any} size="sm" className="capitalize hidden sm:inline-flex">{account.type}</Badge>
              </div>
              <p className="text-[10px] text-slate-500">{account.institution} ...{account.last4}</p>
            </div>
            <div className="text-right">
              <p className={`text-sm font-bold ${account.balance < 0 ? 'text-rose-400' : 'text-slate-200'}`}>
                {account.balance < 0 ? '-' : ''}${Math.abs(account.balance).toLocaleString()}
              </p>
              {account.change !== undefined && (
                <div className={`flex items-center gap-0.5 justify-end text-[10px] ${account.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {account.change >= 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                  <span>{account.change >= 0 ? '+' : ''}{account.change < 0 ? '-' : ''}${Math.abs(account.change).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
