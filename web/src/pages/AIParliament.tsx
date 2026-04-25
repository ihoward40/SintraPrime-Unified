import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Gavel,
  Scale,
  TrendingUp,
  Shield,
  BookOpen,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { clsx } from 'clsx';

const agents = [
  {
    id: 'a1',
    name: 'Lex',
    role: 'Lead Attorney AI',
    specialty: 'Constitutional & Civil Rights Law',
    color: '#D4AF37',
    icon: Scale,
    vote: 'yes',
    confidence: 91,
    reasoning:
      'Strong disparate impact precedent. Inclusive Communities Project (2015) directly supports. Recommend pursuit.',
  },
  {
    id: 'a2',
    name: 'Clio',
    role: 'Research & Precedent AI',
    specialty: 'Case Law Analysis & Research',
    color: '#3B82F6',
    icon: BookOpen,
    vote: 'yes',
    confidence: 88,
    reasoning:
      '43 directly analogous cases found. Win rate: 67% in S.D.N.Y. Statistical evidence pattern matches.',
  },
  {
    id: 'a3',
    name: 'Justice',
    role: 'Strategy AI',
    specialty: 'Litigation Strategy & Risk',
    color: '#10B981',
    icon: Shield,
    vote: 'yes',
    confidence: 79,
    reasoning:
      'Settlement leverage strong. Recommend preliminary injunction to force early resolution at $500K+.',
  },
  {
    id: 'a4',
    name: 'Arbiter',
    role: 'Financial Impact AI',
    specialty: 'Case Valuation & Economics',
    color: '#8B5CF6',
    icon: TrendingUp,
    vote: 'abstain',
    confidence: 65,
    reasoning:
      'Estimated recovery $180K-$520K. Legal costs $45K-$80K. ROI positive but uncertain. Watch discovery.',
  },
  {
    id: 'a5',
    name: 'Prudence',
    role: 'Risk Assessment AI',
    specialty: 'Legal Risk & Compliance',
    color: '#F59E0B',
    icon: AlertCircle,
    vote: 'no',
    confidence: 72,
    reasoning:
      'Standing issue may be dispositive. Judge Williams has dismissed 3 similar housing claims recently.',
  },
  {
    id: 'a6',
    name: 'Magnus',
    role: 'Precedent Navigator AI',
    specialty: 'Federal Appeals & SCOTUS',
    color: '#F43F5E',
    icon: Gavel,
    vote: 'yes',
    confidence: 84,
    reasoning:
      'Circuit precedent clear. 2nd Circuit 2-1 majority for disparate impact. SCOTUS unlikely to revisit.',
  },
];

const pastDecisions = [
  {
    id: 'd1',
    topic: 'Case #2024-BK-0394 - Pursue Chapter 11 Appeal?',
    decision: 'Pursue Appeal',
    date: '2024-06-18',
    confidence: 84,
    votes: { yes: 5, no: 1, abstain: 0 },
    outcome: 'pending',
  },
  {
    id: 'd2',
    topic: 'Accept $180K settlement in Case #2023-CV-4412?',
    decision: 'Accept Settlement',
    date: '2024-06-10',
    confidence: 91,
    votes: { yes: 6, no: 0, abstain: 0 },
    outcome: 'completed',
  },
  {
    id: 'd3',
    topic: 'File preliminary injunction in housing case?',
    decision: 'File Injunction',
    date: '2024-05-28',
    confidence: 77,
    votes: { yes: 4, no: 1, abstain: 1 },
    outcome: 'granted',
  },
  {
    id: 'd4',
    topic: 'Expand practice to securities litigation?',
    decision: 'Defer Decision',
    date: '2024-05-15',
    confidence: 58,
    votes: { yes: 2, no: 2, abstain: 2 },
    outcome: 'deferred',
  },
];

const debateMessages = [
  {
    agentId: 'a2',
    time: '14:02:31',
    text: 'I have identified 43 directly analogous cases in the 2nd Circuit. The win rate for disparate impact FHA claims in SDNY is 67% over the last decade.',
  },
  {
    agentId: 'a5',
    time: '14:02:47',
    text: 'Caution warranted. Judge Williams dismissed three similar housing cases in the last 18 months. Standing issue with prospective tenants needs resolution first.',
  },
  {
    agentId: 'a1',
    time: '14:03:12',
    text: 'Standing argument is addressable. Texas Dept. of Housing v. Inclusive Communities (2015) broadly construed FHA standing. Statistical evidence of discriminatory effect is our strongest argument.',
  },
  {
    agentId: 'a6',
    time: '14:03:28',
    text: 'Agreed. 2nd Circuit precedent is clear on disparate impact. Circuit has not ruled contrary to Inclusive Communities. SCOTUS cert petition on this issue was denied in 2023.',
  },
  {
    agentId: 'a4',
    time: '14:03:45',
    text: 'Financial modeling complete. Expected recovery range: $180K-$520K with 73% probability. Legal costs estimated $45-80K. Positive ROI scenario in 67% of modeled outcomes.',
  },
  {
    agentId: 'a3',
    time: '14:04:02',
    text: 'Strategic recommendation: file for preliminary injunction immediately. Creates settlement leverage and forces defendant to disclose policy documents in discovery. Recommend 90-day aggressive timeline.',
  },
];

export default function AIParliament() {
  const [visibleMessages, setVisibleMessages] = useState(debateMessages.slice(0, 3));
  const [humanDecision, setHumanDecision] = useState<string | null>(null);

  const yesVotes = agents.filter((a) => a.vote === 'yes').length;
  const noVotes = agents.filter((a) => a.vote === 'no').length;
  const abstainVotes = agents.filter((a) => a.vote === 'abstain').length;
  const avgConfidence = Math.round(
    agents.reduce((s, a) => s + a.confidence, 0) / agents.length
  );

  const barData = [
    { name: 'Pursue', value: yesVotes, color: '#10B981' },
    { name: 'Decline', value: noVotes, color: '#F43F5E' },
    { name: 'Abstain', value: abstainVotes, color: '#F59E0B' },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleMessages((prev) => {
        if (prev.length < debateMessages.length) {
          return [...prev, debateMessages[prev.length]];
        }
        return prev;
      });
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const getAgentById = (id: string) => agents.find((a) => a.id === id);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">AI Parliament</h1>
          <p className="text-slate-500 text-sm mt-1">
            6-agent deliberative AI system for legal and strategic decisions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="green" dot>
            Session Active
          </Badge>
          <Button variant="outline" size="sm" icon={Gavel}>
            New Question
          </Button>
        </div>
      </div>

      {/* Active Session */}
      <Card gold padding="lg">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gold/15 flex items-center justify-center">
              <Brain className="w-5 h-5 text-gold" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                Current Question
              </p>
              <h2 className="text-lg font-bold text-slate-100">
                Should we pursue Case #2024-CV-1847 aggressively or seek early settlement?
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Clock className="w-3.5 h-3.5" />
            <span>Deliberating 4:32</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          {[
            {
              label: 'Pursue Aggressively',
              count: yesVotes,
              color: 'text-emerald-400',
              bg: 'bg-emerald-500/10 border-emerald-500/20',
            },
            {
              label: 'Seek Settlement',
              count: noVotes,
              color: 'text-rose-400',
              bg: 'bg-rose-500/10 border-rose-500/20',
            },
            {
              label: 'Need More Info',
              count: abstainVotes,
              color: 'text-amber-400',
              bg: 'bg-amber-500/10 border-amber-500/20',
            },
          ].map((item) => (
            <div
              key={item.label}
              className={clsx('p-3 rounded-xl border text-center', item.bg)}
            >
              <div className={clsx('text-2xl font-bold', item.color)}>{item.count}</div>
              <div className="text-xs text-slate-500 mt-0.5">{item.label}</div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between p-3 bg-gold/5 border border-gold/20 rounded-xl">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-gold" />
            <span className="text-sm font-semibold text-gold">
              Preliminary Decision: Pursue Aggressively
            </span>
          </div>
          <div className="text-sm text-slate-400">
            Avg. Confidence:{' '}
            <span className="text-gold font-bold">{avgConfidence}%</span>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Agent panels */}
        <div className="xl:col-span-2 space-y-4">
          <Card padding="lg">
            <CardHeader
              title="Agent Votes & Reasoning"
              subtitle="6 specialized AI legal agents"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {agents.map((agent, i) => {
                const Icon = agent.icon;
                return (
                  <motion.div
                    key={agent.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className="p-3 bg-slate-800/30 rounded-xl border border-slate-700/30"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{
                          background: agent.color + '20',
                          border: `1px solid ${agent.color}40`,
                        }}
                      >
                        <Icon className="w-4 h-4" style={{ color: agent.color }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-bold" style={{ color: agent.color }}>
                            {agent.name}
                          </span>
                          <Badge
                            variant={
                              agent.vote === 'yes'
                                ? 'green'
                                : agent.vote === 'no'
                                ? 'red'
                                : 'amber'
                            }
                            size="sm"
                          >
                            {agent.vote === 'yes'
                              ? 'Pursue'
                              : agent.vote === 'no'
                              ? 'Decline'
                              : 'Abstain'}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-500">{agent.role}</p>
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-slate-500">Confidence</span>
                            <span
                              className="font-medium"
                              style={{ color: agent.color }}
                            >
                              {agent.confidence}%
                            </span>
                          </div>
                          <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: agent.confidence + '%' }}
                              transition={{ duration: 0.7, delay: i * 0.1 }}
                              className="h-full rounded-full"
                              style={{ background: agent.color }}
                            />
                          </div>
                        </div>
                        <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                          {agent.reasoning}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </Card>

          {/* Live Debate */}
          <Card padding="lg">
            <CardHeader
              title="Live Debate Transcript"
              action={
                <Badge variant="green" dot>
                  Live
                </Badge>
              }
            />
            <div className="space-y-3 max-h-64 overflow-y-auto">
              <AnimatePresence>
                {visibleMessages.map((msg, i) => {
                  const agent = getAgentById(msg.agentId);
                  if (!agent) return null;
                  const Icon = agent.icon;
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4 }}
                      className="flex items-start gap-3"
                    >
                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{ background: agent.color + '20' }}
                      >
                        <Icon className="w-3.5 h-3.5" style={{ color: agent.color }} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="text-xs font-bold"
                            style={{ color: agent.color }}
                          >
                            {agent.name}
                          </span>
                          <span className="text-[10px] text-slate-600 font-mono">
                            {msg.time}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed">{msg.text}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card padding="md">
            <CardHeader title="Vote Distribution" />
            <div className="h-32">
              <ResponsiveContainer>
                <BarChart data={barData} barSize={32}>
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis hide />
                  <Tooltip
                    contentStyle={{
                      background: '#0F172A',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                  />
                  <Bar dataKey="value" radius={4}>
                    {barData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card padding="md">
            <CardHeader
              title="Human Override"
              subtitle="Override AI decision if needed"
            />
            <div className="space-y-2">
              {[
                'Pursue Aggressively',
                'Seek Settlement',
                'Continue Research',
                'Table Discussion',
              ].map((option) => (
                <button
                  key={option}
                  onClick={() => setHumanDecision(option)}
                  className={clsx(
                    'w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all border',
                    humanDecision === option
                      ? 'bg-gold/10 border-gold/40 text-gold'
                      : 'border-slate-700/40 text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                  )}
                >
                  {option}
                </button>
              ))}
              {humanDecision && (
                <Button fullWidth icon={CheckCircle}>
                  Confirm Override
                </Button>
              )}
            </div>
          </Card>

          <Card padding="md">
            <CardHeader title="Decision History" />
            <div className="space-y-2">
              {pastDecisions.map((d) => (
                <div key={d.id} className="p-2.5 bg-slate-800/30 rounded-xl">
                  <p className="text-xs font-medium text-slate-300 leading-snug mb-1">
                    {d.topic}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gold font-semibold">
                      {d.decision}
                    </span>
                    <Badge
                      variant={
                        d.outcome === 'completed' || d.outcome === 'granted'
                          ? 'green'
                          : d.outcome === 'pending'
                          ? 'amber'
                          : 'slate'
                      }
                      size="sm"
                    >
                      {d.outcome}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-600">
                    <span>{d.date}</span>
                    <span>·</span>
                    <span>{d.confidence}% confidence</span>
                    <span>·</span>
                    <span>
                      {d.votes.yes}/{agents.length} yes
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
