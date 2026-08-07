import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock,
  GitBranch,
  Network,
  ShieldCheck,
  TerminalSquare,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';

const agents = [
  { name: 'Hermes', role: 'Planner and coding coordinator', state: 'Planning mock run', load: 72, color: 'text-blue-400' },
  { name: 'Sintra Sentinel', role: 'Monitoring, security, failure review', state: 'Checking disagreement', load: 58, color: 'text-emerald-400' },
  { name: 'Justice Scribe', role: 'Legal-information and document review', state: 'Evidence pending', load: 41, color: 'text-gold' },
  { name: 'Dispatch Marshal', role: 'Customer and communication workflows', state: 'Approval gated', load: 35, color: 'text-sky-400' },
];

const lanes = [
  { label: 'Build', value: 'PASS', icon: CheckCircle2, tone: 'text-emerald-400', detail: 'Production bundle current' },
  { label: 'Console', value: '0', icon: TerminalSquare, tone: 'text-emerald-400', detail: 'Errors in last run' },
  { label: 'Approvals', value: '1', icon: ShieldCheck, tone: 'text-gold', detail: 'Principal decision requested' },
  { label: 'Branches', value: 'clean', icon: GitBranch, tone: 'text-blue-400', detail: 'No visual branch drift' },
];

const orchestrationNodes = [
  { role: 'PLANNER', provider: 'reasoning_model', status: 'COMPLETED', confidence: '76%' },
  { role: 'WORKER', provider: 'coding_model', status: 'COMPLETED', confidence: '80%' },
  { role: 'CHECKER', provider: 'checker_model', status: 'DISPUTED', confidence: '55%' },
  { role: 'RECONCILER', provider: 'reasoning_model', status: 'APPROVAL_REQUIRED', confidence: '54%' },
];

const events = [
  { time: 'Now', title: 'Mock orchestration visible', detail: 'Operations Floor maps roles to governed agents', status: 'complete' },
  { time: '2 min', title: 'Checker disagreement preserved', detail: 'External action boundary remains unresolved', status: 'pending' },
  { time: '5 min', title: 'Principal approval requested', detail: 'No model may approve the high-risk result', status: 'pending' },
];

export default function OperationsFloor() {
  return (
    <div className="space-y-6 overflow-x-hidden" data-testid="operations-floor">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
      >
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <Activity className="h-5 w-5 text-gold" />
            <Badge variant="green" size="sm" dot>Live Floor</Badge>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Operations Floor</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Governed workspace for agent activity, approvals, build evidence, orchestration state, and repair status.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-400">
          <CheckCircle2 className="h-4 w-4" />
          Mock providers only
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {lanes.map((lane, index) => {
          const Icon = lane.icon;
          return (
            <motion.div key={lane.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
              <Card padding="md">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{lane.label}</p>
                    <p className="mt-2 text-xl font-semibold text-slate-100">{lane.value}</p>
                    <p className="mt-1 text-xs text-slate-500">{lane.detail}</p>
                  </div>
                  <div className="rounded-lg bg-slate-800/70 p-2">
                    <Icon className={`h-5 w-5 ${lane.tone}`} />
                  </div>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card padding="lg">
            <CardHeader title="Agent Workstations" subtitle="Current governed role mapping" />
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              {agents.map((agent) => (
                <div key={agent.name} className="min-w-0 rounded-lg border border-slate-700/40 bg-slate-800/25 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-700/50 bg-slate-900/80">
                      <Bot className={`h-5 w-5 ${agent.color}`} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-100">{agent.name}</p>
                      <p className="truncate text-xs text-slate-500">{agent.role}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-slate-400">{agent.state}</span>
                    <span className="shrink-0 text-slate-500">{agent.load}%</span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-gold" style={{ width: `${agent.load}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card padding="lg">
          <CardHeader title="Evidence Queue" subtitle="Mock orchestration timeline" />
          <div className="space-y-4">
            {events.map((event) => (
              <div key={event.title} className="flex gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800/70">
                  {event.status === 'complete' ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Clock className="h-4 w-4 text-gold" />}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-slate-200">{event.title}</p>
                    {event.status === 'pending' && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">{event.detail}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-600">{event.time}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card padding="lg">
        <CardHeader title="Adaptive Orchestration Activity" subtitle="Current mock run, graph, providers, checker result, approval, and outcome" />
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
          {orchestrationNodes.map((node) => (
            <div key={node.role} className="min-w-0 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <Network className="h-4 w-4 shrink-0 text-blue-400" />
                  <p className="truncate text-sm font-semibold text-slate-100">{node.role}</p>
                </div>
                <span className="shrink-0 rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{node.status}</span>
              </div>
              <p className="truncate text-xs text-slate-500">Provider: {node.provider}</p>
              <p className="mt-1 text-xs text-slate-500">Confidence: {node.confidence}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <FloorFact label="Budget Used" value="5 nodes / $0.00" />
          <FloorFact label="Checker Result" value="DISPUTED" />
          <FloorFact label="Final Outcome" value="Principal decision required" />
        </div>
      </Card>
    </div>
  );
}

function FloorFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}