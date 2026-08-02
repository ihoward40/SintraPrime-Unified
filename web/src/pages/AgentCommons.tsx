import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Bot, CheckCircle2, MessageSquare, Network, Play, RefreshCw, Send, ShieldCheck, XCircle } from 'lucide-react';
import { clsx } from 'clsx';

type AgentStatus = { agent_id: string; health: Record<string, unknown>; capabilities: string[] };
type Run = { run_id: string; task_id: string; objective: string; status: string; builder_agent: string; reviewer_agent: string; approval_id?: string | null; reconciliation?: Record<string, unknown> | null };
type StreamEvent = { type: string; data?: Run; actor_id?: string };
const API = '/api/v1/agent-commons';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { ...authHeaders(), ...(init?.headers || {}) } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || 'Agent Commons request failed');
  }
  return response.json() as Promise<T>;
}

export default function AgentCommons() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [objective, setObjective] = useState('');
  const [builder, setBuilder] = useState('codex');
  const [reviewer, setReviewer] = useState('claude-code');
  const [connection, setConnection] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadAgents = useCallback(async () => {
    try {
      const result = await api<{ agents: AgentStatus[] }>('/agents');
      setAgents(result.agents);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load agents');
    }
  }, []);

  useEffect(() => { void loadAgents(); }, [loadAgents]);

  useEffect(() => {
    const controller = new AbortController();
    const connect = async () => {
      setConnection('connecting');
      try {
        const response = await fetch(`${API}/events`, { headers: authHeaders(), signal: controller.signal });
        if (!response.ok || !response.body) throw new Error('Event stream unavailable');
        setConnection('live');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split('\n\n');
          buffer = frames.pop() || '';
          for (const frame of frames) {
            const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
            if (!dataLine) continue;
            const event = JSON.parse(dataLine.slice(6)) as StreamEvent;
            if (event.data) setRuns((current) => [event.data!, ...current.filter((run) => run.run_id !== event.data!.run_id)].slice(0, 50));
          }
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setConnection('offline');
          setError(reason instanceof Error ? reason.message : 'Event stream disconnected');
        }
      }
    };
    void connect();
    return () => controller.abort();
  }, []);

  const pendingApprovals = useMemo(() => runs.filter((run) => run.status === 'waiting_approval'), [runs]);

  async function submitObjective(event: FormEvent) {
    event.preventDefault();
    if (!objective.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const run = await api<Run>('/objectives', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: 'sintraprime-unified', channel_id: 'command-center', thread_id: crypto.randomUUID(),
          objective: objective.trim(), builder_agent: builder, reviewer_agent: reviewer,
          acceptance_criteria: ['Provide evidence', 'Respect owner authority', 'Do not perform prohibited external actions'],
          requested_actions: [], idempotency_key: crypto.randomUUID(),
        }),
      });
      setRuns((current) => [run, ...current.filter((item) => item.run_id !== run.run_id)]);
      setObjective('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to submit objective');
    } finally {
      setSubmitting(false);
    }
  }

  async function decide(run: Run, approved: boolean) {
    try {
      const updated = await api<Run>(`/runs/${run.run_id}/${approved ? 'approve' : 'reject'}`, {
        method: 'POST', body: JSON.stringify({ note: approved ? 'Approved in Agent Commons' : 'Rejected in Agent Commons' }),
      });
      setRuns((current) => [updated, ...current.filter((item) => item.run_id !== updated.run_id)]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Approval action failed');
    }
  }

  return <div className="space-y-6 pb-10">
    <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-gold"><Network className="h-4 w-4" /> SintraPrime Agent Commons</div><h1 className="text-3xl font-semibold text-white">Governed coordination for every agent</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Live agent health, supervised delegation, independent review, durable traces, and authenticated owner decisions.</p></div><div className={clsx('inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-wide', connection === 'live' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : connection === 'connecting' ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' : 'border-rose-500/30 bg-rose-500/10 text-rose-300')}><Play className="h-3.5 w-3.5" /> {connection}</div></section>
    {error && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</div>}
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Agents registered" value={String(agents.length)} detail="Provider-neutral adapters" icon={Bot} /><Metric label="Supervisor runs" value={String(runs.length)} detail="Current browser session" icon={Activity} /><Metric label="Pending approvals" value={String(pendingApprovals.length)} detail="Firm-admin authentication required" icon={MessageSquare} /><Metric label="Governance" value="Protected" detail="External actions default-deny" icon={ShieldCheck} /></section>
    <section className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]"><aside className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-white">Connected agents</h2><button onClick={() => void loadAgents()} className="rounded-lg p-2 text-slate-500 hover:bg-slate-800 hover:text-white"><RefreshCw className="h-4 w-4" /></button></div><div className="mt-4 space-y-3">{agents.map((agent) => <div key={agent.agent_id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3"><div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /><span className="text-sm font-semibold text-white">{agent.agent_id}</span></div><div className="mt-2 flex flex-wrap gap-1">{agent.capabilities.map((capability) => <span key={capability} className="rounded-md bg-slate-800 px-2 py-1 text-[10px] text-slate-400">{capability}</span>)}</div></div>)}</div></aside>
      <main className="space-y-4"><form onSubmit={submitObjective} className="rounded-2xl border border-gold/20 bg-gradient-to-br from-gold/10 to-slate-900/70 p-5"><h2 className="text-lg font-semibold text-white">New supervised objective</h2><textarea value={objective} onChange={(event) => setObjective(event.target.value)} className="mt-4 min-h-28 w-full rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-sm text-white outline-none focus:border-gold/50" placeholder="Describe the outcome. The supervisor will delegate to a builder and independent reviewer." /><div className="mt-3 grid gap-3 sm:grid-cols-2"><select value={builder} onChange={(event) => setBuilder(event.target.value)} className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm text-white">{agents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.agent_id} — builder</option>)}</select><select value={reviewer} onChange={(event) => setReviewer(event.target.value)} className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm text-white">{agents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.agent_id} — reviewer</option>)}</select></div><button disabled={submitting || !objective.trim() || builder === reviewer} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"><Send className="h-4 w-4" /> {submitting ? 'Submitting…' : 'Start supervised run'}</button></form>
        <div className="space-y-3">{runs.map((run) => <article key={run.run_id} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><span className="text-xs font-semibold uppercase tracking-wide text-gold">{run.task_id}</span><span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">{run.status}</span></div><h3 className="mt-2 font-semibold text-white">{run.objective}</h3><p className="mt-1 text-xs text-slate-500">Builder: {run.builder_agent} · Reviewer: {run.reviewer_agent}</p></div>{run.status === 'waiting_approval' && <div className="flex gap-2"><button onClick={() => void decide(run, true)} className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Approve</button><button onClick={() => void decide(run, false)} className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-300"><XCircle className="h-4 w-4" /> Reject</button></div>}</div>{run.reconciliation && <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-400">{JSON.stringify(run.reconciliation, null, 2)}</pre>}</article>)}</div></main></section>
  </div>;
}

function Metric({ label, value, detail, icon: Icon }: { label: string; value: string; detail: string; icon: React.ElementType }) {
  return <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><div className="flex items-start justify-between"><div><p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-white">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div><div className="rounded-xl border border-gold/20 bg-gold/10 p-2 text-gold"><Icon className="h-5 w-5" /></div></div></div>;
}
