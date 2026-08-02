import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  GitBranch,
  MessageSquare,
  Network,
  PauseCircle,
  Play,
  Plus,
  Radio,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
  XCircle,
} from 'lucide-react';
import { clsx } from 'clsx';

type AgentState = 'online' | 'busy' | 'idle' | 'offline';
type TaskState = 'running' | 'review' | 'approval' | 'complete';

interface AgentCard {
  id: string;
  name: string;
  role: string;
  model: string;
  status: AgentState;
  capabilities: string[];
  currentTask?: string;
}

interface TaskCard {
  id: string;
  title: string;
  owner: string;
  reviewer: string;
  state: TaskState;
  updated: string;
  risk: 'low' | 'medium' | 'high';
}

const agents: AgentCard[] = [
  { id: 'supervisor', name: 'Supervisor', role: 'Governed coordinator', model: 'OpenAI adapter', status: 'online', capabilities: ['decompose', 'delegate', 'reconcile', 'escalate'], currentTask: 'Supervising Agent Commons Increment 1' },
  { id: 'hermes', name: 'Hermes', role: 'Orchestrator', model: 'Hermes runtime', status: 'busy', capabilities: ['repository', 'evidence', 'workflow', 'review'], currentTask: 'Collecting implementation evidence' },
  { id: 'codex', name: 'Codex', role: 'Builder', model: 'Coding agent', status: 'busy', capabilities: ['code', 'tests', 'refactor', 'debug'], currentTask: 'Building shared-thread API' },
  { id: 'claude', name: 'Claude Code', role: 'Independent reviewer', model: 'Claude adapter', status: 'idle', capabilities: ['review', 'architecture', 'risk', 'documentation'] },
  { id: 'manus', name: 'Manus', role: 'Implementation worker', model: 'Manus adapter', status: 'idle', capabilities: ['research', 'implementation', 'documents'] },
  { id: 'watchtower', name: 'Watchtower', role: 'Observer', model: 'Monitoring service', status: 'online', capabilities: ['health', 'alerts', 'anomaly detection'] },
];

const tasks: TaskCard[] = [
  { id: 'SPU-20260802-A1', title: 'Persist shared agent threads and provenance', owner: 'Codex', reviewer: 'Claude Code', state: 'running', updated: '2 minutes ago', risk: 'medium' },
  { id: 'SPU-20260802-A2', title: 'Review supervisor policy and owner gates', owner: 'Hermes', reviewer: 'Watchtower', state: 'review', updated: '8 minutes ago', risk: 'high' },
  { id: 'SPU-20260802-A3', title: 'Connect live OpenAI supervisor adapter', owner: 'Supervisor', reviewer: 'Isiah', state: 'approval', updated: '12 minutes ago', risk: 'high' },
  { id: 'SPU-20260802-A4', title: 'Define adapter contract for external agents', owner: 'Manus', reviewer: 'Hermes', state: 'complete', updated: '31 minutes ago', risk: 'low' },
];

const channels = [
  { name: 'command-center', count: 4, active: true },
  { name: 'engineering', count: 7 },
  { name: 'research', count: 3 },
  { name: 'trust-operations', count: 2 },
  { name: 'revenue-lab', count: 5 },
  { name: 'incident-room', count: 0 },
];

const timeline = [
  { agent: 'Supervisor', status: 'ASSIGNED', message: 'Assigned shared-thread persistence to Codex and an independent architecture review to Claude Code.', time: '9:42 AM' },
  { agent: 'Codex', status: 'IN_PROGRESS', message: 'Created tenant-scoped storage and bounded context retrieval. Preparing API surface.', time: '9:45 AM' },
  { agent: 'Hermes', status: 'RESULT', message: 'Governance check confirms merge, deployment, legal dispatch, and financial actions remain owner-controlled.', time: '9:49 AM' },
  { agent: 'Claude Code', status: 'REVIEW', message: 'Review requested: verify tenant isolation, idempotency, loop prevention, and approval transitions.', time: '9:53 AM' },
];

const statusStyles: Record<AgentState, string> = {
  online: 'bg-emerald-400',
  busy: 'bg-amber-400',
  idle: 'bg-blue-400',
  offline: 'bg-slate-600',
};

const taskStateStyles: Record<TaskState, string> = {
  running: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  review: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  approval: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  complete: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
};

function Metric({ label, value, detail, icon: Icon }: { label: string; value: string; detail: string; icon: React.ElementType }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg shadow-black/10">
      <div className="flex items-start justify-between">
        <div><p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-white">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div>
        <div className="rounded-xl border border-gold/20 bg-gold/10 p-2 text-gold"><Icon className="h-5 w-5" /></div>
      </div>
    </div>
  );
}

export default function AgentCommons() {
  const [selectedAgent, setSelectedAgent] = useState('supervisor');
  const [composer, setComposer] = useState('');
  const [autoSupervise, setAutoSupervise] = useState(true);
  const selected = useMemo(() => agents.find((agent) => agent.id === selectedAgent) ?? agents[0], [selectedAgent]);

  return (
    <div className="space-y-6 pb-10">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-gold"><Network className="h-4 w-4" /> SintraPrime Agent Commons</div>
          <h1 className="text-3xl font-semibold text-white">One command center for every agent</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Shared context, supervised delegation, independent review, durable evidence, and owner approval gates in one governed workspace.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-blue-300"><Play className="h-3.5 w-3.5" /> Preview</span>
          <button onClick={() => setAutoSupervise((value) => !value)} className={clsx('inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition', autoSupervise ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-900 text-slate-400')}><Radio className="h-4 w-4" /> Auto-supervise {autoSupervise ? 'on' : 'off'}</button>
          <button className="inline-flex items-center gap-2 rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-yellow-300"><Plus className="h-4 w-4" /> New objective</button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Agents connected" value="6" detail="4 active · 2 standing by" icon={Bot} />
        <Metric label="Open tasks" value="4" detail="1 requires your approval" icon={Activity} />
        <Metric label="Shared threads" value="21" detail="All tenant-scoped and traceable" icon={MessageSquare} />
        <Metric label="Governance state" value="Protected" detail="External actions default-deny" icon={ShieldCheck} />
      </section>

      <section className="grid min-h-[720px] gap-4 xl:grid-cols-[240px_minmax(0,1fr)_330px]">
        <aside className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
          <div className="flex items-center justify-between px-2 py-2"><div><p className="text-xs uppercase tracking-[0.16em] text-slate-500">Workspace</p><p className="mt-1 text-sm font-semibold text-white">SintraPrime Unified</p></div><button className="rounded-lg p-2 text-slate-500 hover:bg-slate-800 hover:text-white"><Search className="h-4 w-4" /></button></div>
          <div className="mt-4"><p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">Channels</p><div className="mt-2 space-y-1">{channels.map((channel) => <button key={channel.name} className={clsx('flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition', channel.active ? 'bg-gold/10 text-gold' : 'text-slate-400 hover:bg-slate-800/70 hover:text-white')}><span className="flex items-center gap-2"><MessageSquare className="h-4 w-4" />{channel.name}</span>{channel.count > 0 && <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">{channel.count}</span>}</button>)}</div></div>
          <div className="mt-6"><div className="flex items-center justify-between px-2"><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">Agents</p><span className="text-[10px] text-emerald-400">6 connected</span></div><div className="mt-2 space-y-1">{agents.map((agent) => <button key={agent.id} onClick={() => setSelectedAgent(agent.id)} className={clsx('flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition', selectedAgent === agent.id ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-800/60')}><div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 text-slate-300"><Bot className="h-4 w-4" /><span className={clsx('absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900', statusStyles[agent.status])} /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{agent.name}</p><p className="truncate text-[11px] text-slate-600">{agent.role}</p></div></button>)}</div></div>
        </aside>

        <main className="flex min-w-0 flex-col rounded-2xl border border-slate-800 bg-slate-900/50">
          <div className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex items-center gap-2"><h2 className="text-lg font-semibold text-white"># command-center</h2><span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">live</span></div><p className="mt-1 text-xs text-slate-500">Supervisor, builders, reviewers, and owner decisions share one durable timeline.</p></div><div className="flex items-center gap-2"><button className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"><Users className="h-4 w-4" /></button><button className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"><GitBranch className="h-4 w-4" /></button><button className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-400 hover:text-white"><Search className="h-4 w-4" /></button></div></div>
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <div className="rounded-2xl border border-gold/20 bg-gradient-to-br from-gold/10 to-transparent p-4"><div className="flex items-start gap-3"><div className="rounded-xl bg-gold/15 p-2 text-gold"><BrainCircuit className="h-5 w-5" /></div><div><p className="text-sm font-semibold text-white">Current objective</p><p className="mt-1 text-sm leading-6 text-slate-300">Build a durable multi-agent workspace where the supervisor can delegate, agents can debate, evidence is preserved, and Isiah remains final authority.</p><div className="mt-3 flex flex-wrap gap-2 text-[11px]"><span className="rounded-full bg-slate-950/60 px-2.5 py-1 text-slate-400">Owner: Isiah</span><span className="rounded-full bg-slate-950/60 px-2.5 py-1 text-slate-400">Builder: Codex</span><span className="rounded-full bg-slate-950/60 px-2.5 py-1 text-slate-400">Reviewer: Claude Code</span></div></div></div></div>
            {timeline.map((item) => <div key={`${item.agent}-${item.time}`} className="flex gap-3"><div className="mt-1 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 text-slate-300"><Bot className="h-4 w-4" /></div><div className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950/40 p-4"><div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-white">{item.agent}</span><span className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-slate-400">{item.status}</span><span className="ml-auto text-[11px] text-slate-600">{item.time}</span></div><p className="mt-2 text-sm leading-6 text-slate-300">{item.message}</p></div></div>)}
          </div>
          <div className="border-t border-slate-800 p-4"><div className="rounded-2xl border border-slate-700 bg-slate-950/70 p-3 focus-within:border-gold/50"><textarea value={composer} onChange={(event) => setComposer(event.target.value)} placeholder="Give the supervisor an objective, tag an agent, or request an independent review…" className="min-h-20 w-full resize-none bg-transparent text-sm text-white outline-none placeholder:text-slate-600" /><div className="mt-2 flex items-center justify-between"><div className="flex gap-2 text-[11px] text-slate-500"><span className="rounded-md bg-slate-900 px-2 py-1">@ agent</span><span className="rounded-md bg-slate-900 px-2 py-1">/ review</span><span className="rounded-md bg-slate-900 px-2 py-1">/ approve</span></div><button disabled={!composer.trim()} className="inline-flex items-center gap-2 rounded-xl bg-gold px-3 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"><Send className="h-3.5 w-3.5" /> Send objective</button></div></div></div>
        </main>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-white">Selected agent</h3><span className={clsx('h-2.5 w-2.5 rounded-full', statusStyles[selected.status])} /></div><div className="mt-4 flex items-center gap-3"><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gold/10 text-gold"><Bot className="h-6 w-6" /></div><div><p className="font-semibold text-white">{selected.name}</p><p className="text-xs text-slate-500">{selected.role}</p></div></div><dl className="mt-4 space-y-3 text-xs"><div className="flex justify-between gap-3"><dt className="text-slate-500">Runtime</dt><dd className="text-right text-slate-300">{selected.model}</dd></div><div className="flex justify-between gap-3"><dt className="text-slate-500">Status</dt><dd className="capitalize text-slate-300">{selected.status}</dd></div><div><dt className="text-slate-500">Capabilities</dt><dd className="mt-2 flex flex-wrap gap-1.5">{selected.capabilities.map((capability) => <span key={capability} className="rounded-md bg-slate-800 px-2 py-1 text-slate-300">{capability}</span>)}</dd></div></dl>{selected.currentTask && <div className="mt-4 rounded-xl border border-blue-500/20 bg-blue-500/10 p-3"><p className="text-[10px] uppercase tracking-[0.16em] text-blue-400">Current task</p><p className="mt-1 text-xs leading-5 text-blue-200">{selected.currentTask}</p></div>}</div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-white">Task queue</h3><button className="text-xs text-gold hover:text-yellow-300">View all</button></div><div className="mt-3 space-y-3">{tasks.map((task) => <button key={task.id} className="w-full rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-left transition hover:border-slate-700"><div className="flex items-start gap-2">{task.state === 'complete' ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-400" /> : task.state === 'approval' ? <PauseCircle className="mt-0.5 h-4 w-4 text-amber-400" /> : <CircleDot className="mt-0.5 h-4 w-4 text-blue-400" />}<div className="min-w-0 flex-1"><p className="text-xs font-medium leading-5 text-slate-200">{task.title}</p><p className="mt-1 text-[10px] text-slate-600">{task.id} · {task.updated}</p></div></div><div className="mt-3 flex items-center justify-between"><span className={clsx('rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase', taskStateStyles[task.state])}>{task.state}</span><ChevronRight className="h-3.5 w-3.5 text-slate-600" /></div></button>)}</div></div>
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 text-amber-400" /><div><p className="text-sm font-semibold text-amber-200">Owner approval required</p><p className="mt-1 text-xs leading-5 text-amber-200/70">Connect the live OpenAI supervisor adapter and authorize its tool allowlist.</p><div className="mt-3 flex gap-2"><button className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/15 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" /> Approve</button><button className="inline-flex items-center gap-1 rounded-lg bg-rose-500/15 px-2.5 py-1.5 text-[11px] font-semibold text-rose-300"><XCircle className="h-3.5 w-3.5" /> Reject</button></div></div></div></div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-white"><Sparkles className="h-4 w-4 text-gold" /> Recommended automation</div><p className="mt-2 text-xs leading-5 text-slate-500">Have the supervisor produce an end-of-day agent recap with completed work, blockers, approvals, and tomorrow's priorities.</p><button className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-gold/40 hover:text-gold"><Clock3 className="h-3.5 w-3.5" /> Configure schedule</button></div>
        </aside>
      </section>
    </div>
  );
}
