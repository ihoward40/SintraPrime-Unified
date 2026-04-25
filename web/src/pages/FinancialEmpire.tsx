import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  CreditCard,
  DollarSign,
  PiggyBank,
  Building,
  Target,
  Filter,
  Star,
  ExternalLink,
  ChevronDown,
  RefreshCw,
  Wallet,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import { format } from 'date-fns';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { useFinancial } from '../hooks/useFinancial';
import { clsx } from 'clsx';

const DONUT_COLORS = ['#D4AF37', '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B'];

function CreditScoreGauge({ score }: { score: number }) {
  const min = 300;
  const max = 850;
  const pct = (score - min) / (max - min);
  const angle = -135 + pct * 270;
  const getColor = (s: number) => s >= 750 ? '#10B981' : s >= 670 ? '#D4AF37' : s >= 580 ? '#F59E0B' : '#F43F5E';
  const getLabel = (s: number) => s >= 750 ? 'Excellent' : s >= 670 ? 'Good' : s >= 580 ? 'Fair' : 'Poor';
  const color = getColor(score);

  const polarToXY = (angleDeg: number, r: number) => {
    const rad = (angleDeg - 90) * Math.PI / 180;
    return { x: 80 + r * Math.cos(rad), y: 80 + r * Math.sin(rad) };
  };

  const arcPath = (startAngle: number, endAngle: number, r: number) => {
    const s = polarToXY(startAngle, r);
    const e = polarToXY(endAngle, r);
    const large = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
  };

  const needleEnd = polarToXY(angle - 90 + 135, 52);

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-40 h-28">
        <svg viewBox="0 0 160 110" className="w-full h-full">
          {/* Background arc */}
          <path d={arcPath(-135, 135, 60)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" strokeLinecap="round" />
          {/* Colored arc */}
          <path d={arcPath(-135, angle - 90 + 135 - 135, 60)} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${color}50)` }} />
          {/* Needle */}
          <line x1="80" y1="80" x2={needleEnd.x} y2={needleEnd.y} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="80" cy="80" r="5" fill={color} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <span className="text-2xl font-bold" style={{ color }}>{score}</span>
          <span className="text-xs" style={{ color }}>{getLabel(score)}</span>
        </div>
      </div>
      <div className="flex gap-2 mt-1">
        <span className="text-xs text-slate-500">300</span>
        <div className="flex-1 h-1 bg-gradient-to-r from-rose-500 via-amber-400 via-gold to-emerald-500 rounded-full" style={{ width: '80px' }} />
        <span className="text-xs text-slate-500">850</span>
      </div>
    </div>
  );
}

export default function FinancialEmpire() {
  const {
    accounts,
    creditScores,
    netWorthHistory,
    fundingOpportunities,
    goals,
    debts,
    filteredFunding,
    netWorth,
    netWorthChange,
    totalAssets,
    totalLiabilities,
    totalDebt,
    toggleSaveFunding,
    setFundingFilter,
  } = useFinancial();

  const [activeTab, setActiveTab] = useState<'overview' | 'funding' | 'debts' | 'goals'>('overview');
  const [fundingTypeFilter, setFundingTypeFilter] = useState('all');
  const [expandedFunding, setExpandedFunding] = useState<string | null>(null);

  const creditScore = creditScores[0];

  const chartData = netWorthHistory.map((e) => ({
    month: format(new Date(e.date), 'MMM'),
    netWorth: e.netWorth,
    assets: e.totalAssets,
  }));

  const assetAllocation = [
    { name: 'Cash & Bank', value: accounts.filter(a => a.balance > 0 && a.accountType === 'checking').reduce((s, a) => s + a.balance, 0) + accounts.filter(a => a.accountType === 'savings').reduce((s, a) => s + a.balance, 0) },
    { name: 'Investments', value: accounts.filter(a => a.accountType === 'investment').reduce((s, a) => s + a.balance, 0) },
    { name: 'Retirement', value: accounts.filter(a => a.accountType === 'retirement').reduce((s, a) => s + a.balance, 0) },
    { name: 'Real Estate', value: 480000 },
    { name: 'Other', value: 45000 },
  ];

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { name: string; value: number }[] }) => {
    if (active && payload?.length) {
      return (
        <div className="glass-card px-3 py-2 rounded-xl text-xs border border-slate-700/60">
          <p className="text-slate-400">{payload[0].name}</p>
          <p className="text-gold font-bold">${payload[0].value.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'funding', label: `Funding (${fundingOpportunities.length})` },
    { id: 'debts', label: 'Debt Elimination' },
    { id: 'goals', label: 'Goals' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Financial Empire</h1>
          <p className="text-slate-500 text-sm mt-1">Net worth · Credit · Funding · Debt elimination</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm" icon={RefreshCw}>Sync Accounts</Button>
          <Button size="sm" icon={TrendingUp}>Full Report</Button>
        </div>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Net Worth', value: `$${(netWorth / 1000).toFixed(0)}K`, change: netWorthChange > 0 ? `+$${(netWorthChange / 1000).toFixed(1)}K this month` : undefined, color: 'text-gold', icon: TrendingUp, bg: 'bg-gold/10' },
          { label: 'Total Assets', value: `$${(totalAssets / 1000).toFixed(0)}K`, color: 'text-emerald-400', icon: Wallet, bg: 'bg-emerald-500/10' },
          { label: 'Total Liabilities', value: `$${(totalLiabilities / 1000).toFixed(0)}K`, color: 'text-rose-400', icon: CreditCard, bg: 'bg-rose-500/10' },
          { label: 'Credit Score', value: creditScore?.score ?? '—', change: creditScore?.change ? `+${creditScore.change} pts` : undefined, color: 'text-blue-400', icon: CreditCard, bg: 'bg-blue-500/10' },
        ].map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="glass-card p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', item.bg)}>
                <item.icon className={clsx('w-4 h-4', item.color)} />
              </div>
            </div>
            <div className={clsx('text-xl font-bold', item.color)}>{item.value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{item.label}</div>
            {item.change && <div className="text-xs text-emerald-400 mt-1">{item.change}</div>}
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900/60 border border-slate-700/40 rounded-xl w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-gold/15 text-gold border border-gold/30' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Net Worth Chart */}
              <div className="xl:col-span-2">
                <Card padding="lg">
                  <CardHeader title="Net Worth Trend" subtitle="12-month performance" />
                  <div className="h-56">
                    <ResponsiveContainer>
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="nwGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#D4AF37" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#D4AF37" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                        <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Area type="monotone" dataKey="netWorth" name="Net Worth" stroke="#D4AF37" strokeWidth={2} fill="url(#nwGrad)" dot={false} activeDot={{ r: 5, fill: '#D4AF37', stroke: '#0F172A', strokeWidth: 2 }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>

              {/* Credit Score + Asset Allocation */}
              <div className="space-y-4">
                <Card padding="md">
                  <CardHeader title="Credit Score" subtitle="Experian · Updated today" />
                  <CreditScoreGauge score={creditScore?.score ?? 742} />
                  <div className="mt-3 space-y-1.5">
                    {(creditScore?.factors ?? []).map((f) => (
                      <div key={f.name} className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">{f.name}</span>
                        <span className={f.impact === 'positive' ? 'text-emerald-400' : f.impact === 'negative' ? 'text-rose-400' : 'text-slate-500'}>
                          {f.impact === 'positive' ? '▲' : f.impact === 'negative' ? '▼' : '–'} {f.weight}%
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card padding="md">
                  <CardHeader title="Asset Allocation" />
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-24">
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie data={assetAllocation} dataKey="value" innerRadius={28} outerRadius={44} strokeWidth={0}>
                            {assetAllocation.map((_, i) => (
                              <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex-1 space-y-1">
                      {assetAllocation.map((item, i) => (
                        <div key={item.name} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full" style={{ background: DONUT_COLORS[i] }} />
                            <span className="text-slate-400">{item.name}</span>
                          </div>
                          <span className="text-slate-300 font-medium">${(item.value / 1000).toFixed(0)}K</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            {/* Bank Accounts */}
            <Card padding="lg">
              <CardHeader title="Connected Accounts" subtitle={`${accounts.length} accounts via Plaid`} action={<Badge variant="green" dot>Synced</Badge>} />
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {accounts.map((acc) => (
                  <div key={acc.id} className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-700/30">
                    <div className="w-9 h-9 rounded-lg bg-slate-700/50 flex items-center justify-center">
                      <Building className="w-4 h-4 text-slate-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{acc.accountName}</p>
                      <p className="text-xs text-slate-500">{acc.institutionName} · {acc.accountNumber}</p>
                    </div>
                    <div className="text-right">
                      <p className={clsx('text-sm font-semibold', acc.balance < 0 ? 'text-rose-400' : 'text-slate-200')}>
                        {acc.balance < 0 ? '-' : ''}${Math.abs(acc.balance).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-xs text-slate-600 capitalize">{acc.accountType.replace(/_/g, ' ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {activeTab === 'funding' && (
          <motion.div key="funding" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-3">
              <select
                value={fundingTypeFilter}
                onChange={(e) => {
                  setFundingTypeFilter(e.target.value);
                  setFundingFilter({ type: e.target.value === 'all' ? undefined : e.target.value });
                }}
                className="input-dark w-auto"
              >
                <option value="all">All Types</option>
                <option value="grant">Grants</option>
                <option value="sba">SBA Loans</option>
                <option value="cdfi">CDFI</option>
                <option value="minority_business">Minority Business</option>
                <option value="women_owned">Women-Owned</option>
                <option value="veteran_owned">Veteran-Owned</option>
              </select>
              <div className="text-sm text-slate-500 flex items-center">
                {filteredFunding.length} opportunities found
              </div>
            </div>

            {/* Funding list */}
            <div className="space-y-3">
              {filteredFunding.map((fund, i) => (
                <motion.div
                  key={fund.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="glass-card overflow-hidden"
                >
                  <div
                    className="flex items-start gap-4 p-4 cursor-pointer"
                    onClick={() => setExpandedFunding(expandedFunding === fund.id ? null : fund.id)}
                  >
                    <div className={clsx(
                      'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                      fund.isGrant ? 'bg-emerald-500/15' : 'bg-blue-500/15'
                    )}>
                      <DollarSign className={fund.isGrant ? 'w-5 h-5 text-emerald-400' : 'w-5 h-5 text-blue-400'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-slate-200">{fund.name}</h3>
                        {fund.isGrant && <Badge variant="green" size="sm">Grant</Badge>}
                        {fund.saved && <Star className="w-3.5 h-3.5 text-gold fill-gold" />}
                      </div>
                      <p className="text-xs text-slate-400">{fund.provider}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs font-medium text-gold">
                          ${fund.amount.min.toLocaleString()} – ${fund.amount.max.toLocaleString()}
                        </span>
                        {fund.deadline && (
                          <span className="text-xs text-amber-400">Due: {fund.deadline}</span>
                        )}
                        {fund.interestRate && (
                          <span className="text-xs text-slate-400">{fund.interestRate}% APR</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleSaveFunding(fund.id); }}
                        className={clsx('p-1.5 rounded-lg transition-colors', fund.saved ? 'text-gold' : 'text-slate-600 hover:text-gold')}
                      >
                        <Star className={clsx('w-4 h-4', fund.saved && 'fill-gold')} />
                      </button>
                      <ChevronDown className={clsx('w-4 h-4 text-slate-500 transition-transform', expandedFunding === fund.id && 'rotate-180')} />
                    </div>
                  </div>

                  <AnimatePresence>
                    {expandedFunding === fund.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-t border-slate-700/40 px-4 pb-4 pt-3"
                      >
                        <p className="text-sm text-slate-300 mb-3">{fund.description}</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Requirements</p>
                            <ul className="space-y-1">
                              {fund.requirements.map((r) => (
                                <li key={r} className="flex items-start gap-2 text-xs text-slate-400">
                                  <span className="text-gold mt-0.5">•</span> {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Eligibility</p>
                            <ul className="space-y-1">
                              {fund.eligibility.map((e) => (
                                <li key={e} className="flex items-start gap-2 text-xs text-slate-400">
                                  <span className="text-emerald-400 mt-0.5">✓</span> {e}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                        {fund.applicationUrl && (
                          <div className="mt-3">
                            <Button variant="outline" size="sm" icon={ExternalLink} iconRight>Apply Now</Button>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'debts' && (
          <motion.div key="debts" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Total Debt', value: `$${(totalDebt / 1000).toFixed(0)}K`, color: 'text-rose-400' },
                { label: 'Avg Interest Rate', value: `${(debts.reduce((s, d) => s + d.interestRate, 0) / debts.length).toFixed(1)}%`, color: 'text-amber-400' },
                { label: 'Monthly Payment', value: `$${debts.reduce((s, d) => s + d.minimumPayment, 0).toLocaleString()}`, color: 'text-blue-400' },
              ].map((item) => (
                <Card key={item.label} padding="md">
                  <div className={clsx('text-2xl font-bold mb-1', item.color)}>{item.value}</div>
                  <div className="text-sm text-slate-500">{item.label}</div>
                </Card>
              ))}
            </div>

            <div className="space-y-3">
              {debts.map((debt, i) => {
                const progress = 100 - (debt.balance / (debt.balance + 50000)) * 100;
                return (
                  <motion.div key={debt.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}>
                    <Card padding="md">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-sm font-semibold text-slate-200">{debt.name}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="slate" size="sm">{debt.type.replace(/_/g, ' ')}</Badge>
                            <Badge variant={debt.strategy === 'avalanche' ? 'red' : 'blue'} size="sm">{debt.strategy}</Badge>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-rose-400">${debt.balance.toLocaleString()}</div>
                          <div className="text-xs text-slate-500">{debt.interestRate}% APR</div>
                        </div>
                      </div>
                      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${progress}%` }}
                          transition={{ duration: 0.8, delay: i * 0.1 }}
                          className="h-full bg-rose-500 rounded-full"
                        />
                      </div>
                      <div className="flex justify-between text-xs text-slate-500">
                        <span>Min: ${debt.minimumPayment.toLocaleString()}/mo</span>
                        <span>Priority #{debt.priority}</span>
                      </div>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}

        {activeTab === 'goals' && (
          <motion.div key="goals" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {goals.map((goal, i) => (
                <motion.div key={goal.id} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
                  <Card padding="lg">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-200">{goal.name}</h3>
                        <Badge variant={goal.onTrack ? 'green' : 'amber'} size="sm" dot className="mt-1">
                          {goal.onTrack ? 'On Track' : 'Needs Attention'}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-gold">{goal.progress.toFixed(0)}%</div>
                      </div>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-3">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, goal.progress)}%` }}
                        transition={{ duration: 0.9, delay: i * 0.1, ease: 'easeOut' }}
                        className={clsx('h-full rounded-full', goal.onTrack ? 'bg-emerald-400' : 'bg-amber-400')}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Current: ${goal.currentAmount.toLocaleString()}</span>
                      <span>Target: ${goal.targetAmount.toLocaleString()}</span>
                    </div>
                    {goal.monthlyContribution > 0 && (
                      <div className="mt-2 text-xs text-slate-500">
                        Contributing ${goal.monthlyContribution.toLocaleString()}/month
                      </div>
                    )}
                    {goal.deadline && (
                      <div className="mt-1 text-xs text-slate-500">
                        Target date: {format(new Date(goal.deadline), 'MMMM yyyy')}
                      </div>
                    )}
                  </Card>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
