import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Gavel,
  Search,
  Plus,
  Filter,
  Calendar,
  Clock,
  AlertCircle,
  ChevronRight,
  ArrowUpRight,
  User,
  Scale,
  FileText,
} from 'lucide-react';
import { format } from 'date-fns';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { useLegalStore } from '../store/legalStore';
import { useCaseSearch } from '../hooks/useCases';
import { clsx } from 'clsx';
import type { Case, CaseStatus } from '../types/legal';

const statusConfig: Record<CaseStatus, { label: string; badge: 'gold' | 'blue' | 'amber' | 'purple' | 'green' | 'slate' | 'red' }> = {
  intake: { label: 'Intake', badge: 'slate' },
  research: { label: 'Research', badge: 'blue' },
  drafting: { label: 'Drafting', badge: 'amber' },
  filing: { label: 'Filing', badge: 'purple' },
  monitoring: { label: 'Monitoring', badge: 'green' },
  closed: { label: 'Closed', badge: 'slate' },
  settlement: { label: 'Settlement', badge: 'gold' },
  appeal: { label: 'Appeal', badge: 'red' },
};

const priorityConfig = {
  critical: { label: 'Critical', badge: 'red' as const },
  high: { label: 'High', badge: 'amber' as const },
  medium: { label: 'Medium', badge: 'blue' as const },
  low: { label: 'Low', badge: 'slate' as const },
};

export default function CaseManagement() {
  const { cases, setActiveCase, activeCaseId } = useLegalStore();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<CaseStatus | 'all'>('all');
  const filtered = useCaseSearch(search, statusFilter !== 'all' ? { status: statusFilter } : undefined);
  const activeCase = cases.find((c) => c.id === activeCaseId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Case Management</h1>
          <p className="text-slate-500 text-sm mt-1">{cases.length} total cases · {cases.filter(c => c.status !== 'closed').length} active</p>
        </div>
        <Button size="sm" icon={Plus}>New Case</Button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Case list */}
        <div className="xl:col-span-2 space-y-3">
          {/* Search + filter */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search cases..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-dark pl-10 py-2 text-sm"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as CaseStatus | 'all')}
              className="input-dark w-auto py-2 text-sm"
            >
              <option value="all">All Status</option>
              {Object.entries(statusConfig).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            {filtered.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => setActiveCase(c.id)}
                className={clsx(
                  'glass-card p-4 cursor-pointer transition-all duration-200 hover:-translate-y-0.5',
                  activeCaseId === c.id && 'border-gold/40 bg-gold/5'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <Badge variant={statusConfig[c.status]?.badge ?? 'slate'} size="sm">
                        {statusConfig[c.status]?.label ?? c.status}
                      </Badge>
                      <Badge variant={priorityConfig[c.priority].badge} size="sm">
                        {priorityConfig[c.priority].label}
                      </Badge>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-200 leading-snug truncate">{c.title}</h3>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">{c.caseNumber}</p>
                    {c.nextDeadline && (
                      <div className="flex items-center gap-1 mt-2">
                        <Clock className="w-3 h-3 text-amber-400" />
                        <span className="text-xs text-amber-400">Due: {format(new Date(c.nextDeadline), 'MMM d')}</span>
                      </div>
                    )}
                  </div>
                  <ChevronRight className={clsx('w-4 h-4 flex-shrink-0 text-slate-600', activeCaseId === c.id && 'text-gold')} />
                </div>
              </motion.div>
            ))}
            {filtered.length === 0 && (
              <div className="py-12 text-center text-slate-500">
                <Gavel className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No cases found</p>
              </div>
            )}
          </div>
        </div>

        {/* Case Detail */}
        <div className="xl:col-span-3">
          <AnimatePresence mode="wait">
            {activeCase ? (
              <motion.div
                key={activeCase.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="space-y-4"
              >
                {/* Case header */}
                <Card padding="lg">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={statusConfig[activeCase.status]?.badge ?? 'slate'}>
                          {statusConfig[activeCase.status]?.label ?? activeCase.status}
                        </Badge>
                        <Badge variant={priorityConfig[activeCase.priority].badge}>
                          {priorityConfig[activeCase.priority].label} Priority
                        </Badge>
                      </div>
                      <h2 className="text-xl font-bold text-slate-100">{activeCase.title}</h2>
                      <p className="text-sm font-mono text-gold mt-1">{activeCase.caseNumber}</p>
                      {activeCase.court && <p className="text-sm text-slate-500 mt-0.5">{activeCase.court}</p>}
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" icon={FileText}>Add Document</Button>
                      <Button size="sm" icon={ArrowUpRight} iconRight>Open Full</Button>
                    </div>
                  </div>

                  {activeCase.description && (
                    <p className="text-sm text-slate-400 leading-relaxed mb-4">{activeCase.description}</p>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {[
                      { label: 'Filed', value: format(new Date(activeCase.filingDate), 'MMM d, yyyy') },
                      { label: 'Next Deadline', value: activeCase.nextDeadline ? format(new Date(activeCase.nextDeadline), 'MMM d, yyyy') : 'None' },
                      { label: 'Practice Area', value: activeCase.practiceArea?.replace(/_/g, ' ') ?? '—' },
                      { label: 'Attorney', value: activeCase.assignedAttorney },
                      { label: 'Est. Value', value: activeCase.estimatedValue ? `$${activeCase.estimatedValue.toLocaleString()}` : '—' },
                      { label: 'Judge', value: activeCase.judge ?? '—' },
                    ].map((item) => (
                      <div key={item.label} className="p-2.5 bg-slate-800/40 rounded-lg">
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">{item.label}</p>
                        <p className="text-sm text-slate-200 mt-0.5">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* AI Analysis */}
                {activeCase.aiAnalysis && (
                  <Card padding="lg">
                    <CardHeader title="AI Case Analysis" subtitle="Generated by SintraPrime AI" />
                    <div className="space-y-4">
                      <div className="flex items-center gap-4">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-gold">
                            {(activeCase.aiAnalysis.successProbability * 100).toFixed(0)}%
                          </div>
                          <div className="text-xs text-slate-500">Success Probability</div>
                        </div>
                        <div className="flex-1">
                          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${activeCase.aiAnalysis.successProbability * 100}%` }}
                              transition={{ duration: 0.8 }}
                              className="h-full bg-gold rounded-full"
                            />
                          </div>
                          <p className="text-xs text-slate-500 mt-1">{activeCase.aiAnalysis.strategyNotes}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Key Issues</p>
                          <ul className="space-y-1">
                            {activeCase.aiAnalysis.keyIssues.map((issue) => (
                              <li key={issue} className="flex items-start gap-2 text-xs text-slate-400">
                                <Scale className="w-3 h-3 text-gold mt-0.5 flex-shrink-0" />
                                {issue}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Recommended Actions</p>
                          <ul className="space-y-1">
                            {activeCase.aiAnalysis.recommendedActions.map((action) => (
                              <li key={action} className="flex items-start gap-2 text-xs text-slate-400">
                                <ChevronRight className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                                {action}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Parties */}
                {activeCase.parties.length > 0 && (
                  <Card padding="lg">
                    <CardHeader title="Parties" />
                    <div className="space-y-2">
                      {activeCase.parties.map((party) => (
                        <div key={party.id} className="flex items-center gap-3 p-2.5 bg-slate-800/30 rounded-lg">
                          <div className="w-8 h-8 rounded-lg bg-slate-700/50 flex items-center justify-center">
                            <User className="w-4 h-4 text-slate-400" />
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-200">{party.name}</p>
                            {party.attorney && <p className="text-xs text-slate-500">Atty: {party.attorney}</p>}
                          </div>
                          <Badge variant="slate" size="sm">{party.role.replace(/_/g, ' ')}</Badge>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-64 flex items-center justify-center border border-dashed border-slate-800 rounded-2xl"
              >
                <div className="text-center text-slate-600">
                  <Gavel className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Select a case to view details</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
