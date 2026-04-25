import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Scale,
  TrendingUp,
  CreditCard,
  PiggyBank,
  Building2,
  FileText,
  Plus,
  Gavel,
  Brain,
  AlertCircle,
  CheckCircle2,
  Clock,
  ArrowRight,
  DollarSign,
  Zap,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { format, formatDistanceToNow } from 'date-fns';
import StatCard from '../components/ui/StatCard';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { useAppStore } from '../store/appStore';
import { useLegalStore } from '../store/legalStore';
import { useFinancialStore } from '../store/financialStore';

const quickActions = [
  { label: 'New Case', icon: Gavel, path: '/cases', color: 'text-gold', bg: 'bg-gold/10' },
  { label: 'Draft Motion', icon: FileText, path: '/legal', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  { label: 'Check Credit', icon: CreditCard, path: '/financial', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { label: 'Find Funding', icon: DollarSign, path: '/financial', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { label: 'AI Parliament', icon: Brain, path: '/ai-parliament', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  { label: 'New Entity', icon: Building2, path: '/entities', color: 'text-rose-400', bg: 'bg-rose-500/10' },
];

const activityLog = [
  { id: 1, type: 'case', icon: Gavel, color: 'text-gold', title: 'Motion to Dismiss filed', subtitle: 'Case #2024-CV-1847', time: '2 hours ago' },
  { id: 2, type: 'financial', icon: TrendingUp, color: 'text-emerald-400', title: 'Credit score updated: 742', subtitle: '+12 points from last month', time: '4 hours ago' },
  { id: 3, type: 'entity', icon: Building2, color: 'text-blue-400', title: 'Sintra Holdings LLC annual report filed', subtitle: 'Delaware • Confirmed #DEL-20240612', time: 'Yesterday' },
  { id: 4, type: 'ai', icon: Brain, color: 'text-purple-400', title: 'AI Parliament decision: Pursue appeal', subtitle: 'Case #2024-BK-0394 • Confidence 84%', time: '2 days ago' },
  { id: 5, type: 'financial', icon: DollarSign, color: 'text-gold', title: 'New funding match: SBA 7(a)', subtitle: 'Up to $5M • Eligibility: High', time: '3 days ago' },
  { id: 6, type: 'case', icon: CheckCircle2, color: 'text-emerald-400', title: 'Settlement reached', subtitle: 'Case #2023-CV-4412 • $180,000', time: '4 days ago' },
];

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-card border border-slate-700/60 px-3 py-2 rounded-xl text-sm">
        <p className="text-slate-400 text-xs mb-1">{label}</p>
        <p className="text-gold font-semibold">${(payload[0].value / 1000).toFixed(0)}K</p>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAppStore();
  const { cases } = useLegalStore();
  const { accounts, creditScores, netWorthHistory, goals } = useFinancialStore();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const activeCases = cases.filter((c) => c.status !== 'closed').length;
  const netWorth = netWorthHistory[netWorthHistory.length - 1]?.netWorth ?? 0;
  const creditScore = creditScores[0]?.score ?? 0;
  const totalAccounts = accounts.reduce((sum, a) => sum + Math.max(0, a.balance), 0);
  const monthlySavings = goals.find((g) => g.type === 'emergency_fund')?.monthlyContribution ?? 3200;

  const statCards = [
    { title: 'Active Cases', value: activeCases, icon: Scale, iconColor: 'text-gold', iconBg: 'bg-gold/10', trend: 'up' as const, change: 8.3, subtitle: `${cases.length} total cases` },
    { title: 'Net Worth', value: `$${(netWorth / 1000).toFixed(0)}K`, icon: TrendingUp, iconColor: 'text-emerald-400', iconBg: 'bg-emerald-500/10', trend: 'up' as const, change: 4.2, subtitle: 'Updated this month', highlight: true },
    { title: 'Credit Score', value: creditScore, icon: CreditCard, iconColor: 'text-blue-400', iconBg: 'bg-blue-500/10', trend: 'up' as const, change: 1.6, subtitle: 'Excellent • Experian' },
    { title: 'Monthly Savings', value: `$${(monthlySavings / 1000).toFixed(1)}K`, icon: PiggyBank, iconColor: 'text-amber-400', iconBg: 'bg-amber-500/10', trend: 'up' as const, change: 12.5, subtitle: '24% of income' },
    { title: 'Entities Managed', value: 7, icon: Building2, iconColor: 'text-purple-400', iconBg: 'bg-purple-500/10', trend: 'neutral' as const, subtitle: '3 LLCs, 2 Trusts, 2 Corps' },
    { title: 'Documents', value: '142', icon: FileText, iconColor: 'text-rose-400', iconBg: 'bg-rose-500/10', trend: 'up' as const, change: 5.1, subtitle: '18 added this month' },
  ];

  const chartData = netWorthHistory.map((entry) => ({
    month: format(new Date(entry.date), 'MMM'),
    value: entry.netWorth,
    assets: entry.totalAssets,
    liabilities: entry.totalLiabilities,
  }));

  const upcomingDeadlines = cases
    .filter((c) => c.nextDeadline)
    .sort((a, b) => new Date(a.nextDeadline!).getTime() - new Date(b.nextDeadline!).getTime())
    .slice(0, 4);

  const getHourGreeting = () => {
    const h = currentTime.getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-start justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {getHourGreeting()}, <span className="text-gold-gradient">{user?.name?.split(' ')[0]}</span> 👋
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            {format(currentTime, 'EEEE, MMMM d, yyyy')} • {format(currentTime, 'h:mm a')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-xs text-emerald-400 font-medium">AI Systems Active</span>
          </div>
        </div>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {statCards.map((card, i) => (
          <StatCard key={card.title} {...card} index={i} />
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Net Worth Chart */}
        <div className="xl:col-span-2">
          <Card padding="lg" animate index={0}>
            <CardHeader
              title="Net Worth Trend"
              subtitle="12-month portfolio performance"
              action={
                <Button variant="ghost" size="sm" icon={ArrowRight} iconRight onClick={() => navigate('/financial')}>
                  Full Report
                </Button>
              }
            />
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#D4AF37" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#D4AF37" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis
                    dataKey="month"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis hide />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#D4AF37"
                    strokeWidth={2}
                    fill="url(#goldGrad)"
                    dot={false}
                    activeDot={{ r: 5, fill: '#D4AF37', stroke: '#0F172A', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card padding="lg" animate index={1}>
          <CardHeader title="Quick Actions" subtitle="Common tasks & shortcuts" />
          <div className="grid grid-cols-2 gap-2">
            {quickActions.map((action) => (
              <motion.button
                key={action.label}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate(action.path)}
                className={`flex flex-col items-center gap-2 p-3 rounded-xl ${action.bg} border border-transparent hover:border-slate-700/50 transition-all duration-200`}
              >
                <action.icon className={`w-5 h-5 ${action.color}`} />
                <span className="text-xs font-medium text-slate-300">{action.label}</span>
              </motion.button>
            ))}
          </div>
        </Card>
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="xl:col-span-2">
          <Card padding="lg" animate index={2}>
            <CardHeader title="Recent Activity" subtitle="Latest actions and updates" />
            <div className="space-y-1">
              {activityLog.map((activity, i) => (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-3 p-3 rounded-xl hover:bg-slate-800/30 transition-colors cursor-pointer group"
                >
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-slate-800/60 ${activity.color}`}>
                    <activity.icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200 group-hover:text-white transition-colors">
                      {activity.title}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{activity.subtitle}</p>
                  </div>
                  <span className="flex-shrink-0 text-xs text-slate-600">{activity.time}</span>
                </motion.div>
              ))}
            </div>
          </Card>
        </div>

        {/* Upcoming Deadlines */}
        <Card padding="lg" animate index={3}>
          <CardHeader
            title="Upcoming Deadlines"
            subtitle="Next 30 days"
            action={
              <Button variant="ghost" size="sm" onClick={() => navigate('/cases')}>View All</Button>
            }
          />
          <div className="space-y-3">
            {upcomingDeadlines.length === 0 ? (
              <div className="text-center py-6 text-slate-500 text-sm">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/40" />
                No upcoming deadlines
              </div>
            ) : (
              upcomingDeadlines.map((c) => {
                const daysUntil = Math.ceil((new Date(c.nextDeadline!).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                const isUrgent = daysUntil <= 7;
                const isWarning = daysUntil <= 14;
                return (
                  <div key={c.id} className="flex items-start gap-3">
                    <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                      isUrgent ? 'bg-rose-500/20 text-rose-400' :
                      isWarning ? 'bg-amber-500/20 text-amber-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {daysUntil}d
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-300 truncate">{c.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {format(new Date(c.nextDeadline!), 'MMM d, yyyy')}
                      </p>
                    </div>
                    {isUrgent && (
                      <AlertCircle className="flex-shrink-0 w-4 h-4 text-rose-400" />
                    )}
                  </div>
                );
              })
            )}

            {/* AI Parliament widget */}
            <div className="mt-4 pt-4 border-t border-slate-800/50">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">AI Parliament</span>
                <Badge variant="green" size="sm" dot>Active</Badge>
              </div>
              <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-xl">
                <p className="text-xs text-slate-300 font-medium">Last Decision:</p>
                <p className="text-xs text-slate-400 mt-1">Appeal Case #2024-BK-0394 — 84% confidence</p>
                <p className="text-xs text-slate-600 mt-1">6/6 agents voted · 2 days ago</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Financial Goals progress */}
      <Card padding="lg" animate index={4}>
        <CardHeader
          title="Financial Goals"
          subtitle="Progress toward your targets"
          action={<Button variant="ghost" size="sm" onClick={() => navigate('/financial')}>Manage Goals</Button>}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {useFinancialStore.getState().goals.map((goal, i) => (
            <div key={goal.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-300 truncate">{goal.name}</span>
                <span className={`text-xs font-semibold ${goal.onTrack ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {goal.progress.toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, goal.progress)}%` }}
                  transition={{ duration: 0.8, delay: i * 0.1, ease: 'easeOut' }}
                  className={`h-full rounded-full ${goal.onTrack ? 'bg-emerald-400' : 'bg-amber-400'}`}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>${(goal.currentAmount / 1000).toFixed(0)}K</span>
                <span>${(goal.targetAmount / 1000).toFixed(0)}K</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
