import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  CircleDollarSign,
  FileDown,
  GitBranch,
  KeyRound,
  Loader2,
  Network,
  Play,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { executeOrchestration, OrchestrationRun } from '../api/orchestration';

const executionModes = [
  'SINGLE',
  'PLAN_AND_EXECUTE',
  'THINK_WORK_CHECK',
  'PARALLEL_COMPARE',
  'RESEARCH_SYNTHESIS',
  'CODE_REVIEW_LOOP',
  'HIGH_ASSURANCE',
];

const initialRun: OrchestrationRun = {
  run_id: 'mock-preview',
  objective: 'Implement governed orchestration with independent checker review.',
  status: 'APPROVAL_REQUIRED',
  execution_mode: 'THINK_WORK_CHECK',
  classification: {
    task_type: 'coding',
    sensitivity: 'CONFIDENTIAL',
    required_roles: ['PLANNER', 'THINKER', 'WORKER', 'CHECKER', 'RECONCILER', 'GOVERNANCE_REVIEWER'],
    approval_requirement: true,
  },
  nodes: [
    { node_id: 'planner-1', role: 'PLANNER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.76, dependencies: [] },
    { node_id: 'thinker-1', role: 'THINKER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.76, dependencies: [] },
    { node_id: 'worker-1', role: 'WORKER', status: 'COMPLETED', assigned_provider: 'coding_model', confidence: 0.8, dependencies: ['thinker-1'] },
    { node_id: 'checker-1', role: 'CHECKER', status: 'COMPLETED', assigned_provider: 'checker_model', confidence: 0.72, dependencies: ['worker-1'] },
    { node_id: 'reconciler-1', role: 'RECONCILER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.76, dependencies: ['checker-1'] },
  ],
  routing_decisions: [
    { selected_provider: 'coding_model', candidate_providers: ['coding_model', 'checker_model'], rejected_providers: [], selection_reason: 'Selected by task fit, role fit, sensitivity policy, and budget.' },
  ],
  budget: {
    input_tokens_used: 0,
    output_tokens_used: 0,
    provider_cost_used: 0,
    nodes_used: 5,
    retries_used: 0,
    hard_limit_reached: false,
  },
  verification: [
    {
      verification_result: 'DISPUTED',
      confidence_score: 0.55,
      evidence_quality: 'test',
      contradictions: ['Worker output did not prove external action remained disabled.'],
      unresolved_uncertainty: ['External action boundary must be confirmed.'],
    },
  ],
  reconciliation: {
    verified_result: { claims: [] },
    supported_inference: [],
    unresolved_issue: ['External action boundary must be confirmed.'],
    principal_decision_required: ['Principal review recommended for unresolved disagreement.'],
    disputed_claims: [{ claim: 'Worker output did not prove external action remained disabled.', resolution: 'unresolved' }],
    final_confidence: 0.54,
  },
  approvals: [
    { approval_id: 'approval-preview', requested_action: 'Approve governed orchestration result', reason: 'Approval required by policy or unresolved disagreement.', status: 'REQUESTED' },
  ],
  events: [
    { sequence: 1, event_type: 'RUN_PLANNED', actor_role: 'PLANNER', created_at: 'mock' },
    { sequence: 2, event_type: 'NODE_COMPLETED', actor_role: 'WORKER', created_at: 'mock' },
    { sequence: 3, event_type: 'APPROVAL_REQUESTED', actor_role: 'GOVERNANCE_REVIEWER', created_at: 'mock' },
  ],
};

export default function OrchestrationCommandCenter() {
  const [objective, setObjective] = useState(initialRun.objective);
  const [constraints, setConstraints] = useState('No external providers. Preserve Principal approval.');
  const [mode, setMode] = useState('THINK_WORK_CHECK');
  const [sensitivity, setSensitivity] = useState('CONFIDENTIAL');
  const [maxNodes, setMaxNodes] = useState(12);
  const [maxTokens, setMaxTokens] = useState(8000);
  const [run, setRun] = useState<OrchestrationRun>(initialRun);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const roleSummary = useMemo(() => run.nodes.reduce<Record<string, number>>((acc, node) => {
    acc[node.role] = (acc[node.role] || 0) + 1;
    return acc;
  }, {}), [run.nodes]);

  async function startRun() {
    setLoading(true);
    setError(null);
    try {
      const nextRun = await executeOrchestration({
        objective,
        execution_mode: mode,
        constraints: { notes: constraints, sensitivity },
        budget_limits: {
          maximum_input_tokens: maxTokens,
          maximum_output_tokens: 4000,
          maximum_provider_cost: 0,
          maximum_nodes: maxNodes,
          maximum_retries: 2,
          maximum_execution_time: 300,
          approved_providers: ['reasoning_model', 'coding_model', 'research_model', 'checker_model', 'security_model'],
          approved_task_types: [],
        },
      });
      setRun(nextRun);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start orchestration run');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5 overflow-x-hidden" data-testid="orchestration-command-center">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-emerald-400">
            <Network className="h-4 w-4" />
            Mock orchestration only
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Orchestration Command Center</h1>
        </div>
        <button
          type="button"
          onClick={startRun}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-gold px-4 text-sm font-semibold text-slate-950 hover:bg-gold/90 disabled:opacity-60"
          disabled={loading}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Start Mock Run
        </button>
      </div>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-100">
            <SlidersHorizontal className="h-4 w-4 text-gold" />
            New Run
          </div>
          <label className="block text-xs font-medium text-slate-400">Objective</label>
          <textarea value={objective} onChange={(event) => setObjective(event.target.value)} className="mt-1 h-24 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 outline-none focus:border-gold" />
          <label className="mt-3 block text-xs font-medium text-slate-400">Constraints</label>
          <textarea value={constraints} onChange={(event) => setConstraints(event.target.value)} className="mt-1 h-20 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 outline-none focus:border-gold" />
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <Field label="Execution Mode">
              <select value={mode} onChange={(event) => setMode(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none focus:border-gold">
                {executionModes.map((item) => <option key={item}>{item}</option>)}
              </select>
            </Field>
            <Field label="Sensitivity">
              <select value={sensitivity} onChange={(event) => setSensitivity(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none focus:border-gold">
                {['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', 'PRIVILEGED'].map((item) => <option key={item}>{item}</option>)}
              </select>
            </Field>
            <Field label="Max Nodes">
              <input value={maxNodes} onChange={(event) => setMaxNodes(Number(event.target.value))} min={1} type="number" className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none focus:border-gold" />
            </Field>
            <Field label="Input Tokens">
              <input value={maxTokens} onChange={(event) => setMaxTokens(Number(event.target.value))} min={1} type="number" className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none focus:border-gold" />
            </Field>
          </div>
          {error && <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-4 2xl:grid-cols-3">
          <Panel title="Execution Graph" icon={<GitBranch className="h-4 w-4 text-blue-400" />} className="2xl:col-span-2">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {run.nodes.map((node) => (
                <div key={node.node_id} className="min-w-0 rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-100">{node.role}</p>
                      <p className="truncate text-xs text-slate-500">{node.node_id}</p>
                    </div>
                    <Status value={node.status} />
                  </div>
                  <p className="mt-3 truncate text-xs text-slate-400">{node.assigned_provider || 'Unassigned'}</p>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-emerald-400" style={{ width: `${Math.round((node.confidence || 0) * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Budget" icon={<CircleDollarSign className="h-4 w-4 text-emerald-400" />}>
            <Metric label="Nodes" value={run.budget.nodes_used} />
            <Metric label="Retries" value={run.budget.retries_used} />
            <Metric label="Provider Cost" value={`$${run.budget.provider_cost_used.toFixed(2)}`} />
            <Metric label="Limit" value={run.budget.hard_limit_reached ? run.budget.limit_reason || 'Reached' : 'Clear'} />
          </Panel>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Panel title="Roles" icon={<ShieldCheck className="h-4 w-4 text-emerald-400" />}>
          {Object.entries(roleSummary).map(([role, count]) => <Metric key={role} label={role} value={count} />)}
        </Panel>
        <Panel title="Evidence And Confidence" icon={<CheckCircle2 className="h-4 w-4 text-blue-400" />}>
          <Metric label="Classification" value={run.classification.task_type} />
          <Metric label="Sensitivity" value={run.classification.sensitivity} />
          <Metric label="Final Confidence" value={run.reconciliation ? `${Math.round(run.reconciliation.final_confidence * 100)}%` : 'Pending'} />
          <Metric label="Checker" value={run.verification[0]?.verification_result || 'Pending'} />
        </Panel>
        <Panel title="Approval" icon={<KeyRound className="h-4 w-4 text-gold" />}>
          {run.approvals.length ? run.approvals.map((approval) => (
            <div key={approval.approval_id} className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-amber-200">{approval.status}</p>
                <AlertTriangle className="h-4 w-4 text-amber-300" />
              </div>
              <p className="mt-2 text-xs text-amber-100/80">{approval.reason}</p>
            </div>
          )) : <p className="text-sm text-slate-500">No Principal approval pending.</p>}
        </Panel>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
        <Panel title="Final Reconciled Result" icon={<FileDown className="h-4 w-4 text-gold" />}>
          <pre className="max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(run.reconciliation || {}, null, 2)}</pre>
        </Panel>
        <Panel title="Event Timeline" icon={<Network className="h-4 w-4 text-blue-400" />}>
          <div className="space-y-2">
            {run.events.map((event) => (
              <div key={event.sequence} className="flex items-center justify-between gap-3 rounded-lg bg-slate-950/60 px-3 py-2">
                <span className="truncate text-xs text-slate-300">{event.sequence}. {event.event_type}</span>
                <span className="shrink-0 text-[11px] text-slate-500">{event.actor_role || 'SYSTEM'}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block min-w-0">
      <span className="text-xs font-medium text-slate-400">{label}</span>
      {children}
    </label>
  );
}

function Panel({ title, icon, className, children }: { title: string; icon: React.ReactNode; className?: string; children: React.ReactNode }) {
  return (
    <div className={`min-w-0 rounded-lg border border-slate-800 bg-slate-900/60 p-4 ${className || ''}`}>
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-100">{icon}{title}</div>
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-800 py-2 last:border-b-0">
      <span className="min-w-0 truncate text-xs text-slate-500">{label}</span>
      <span className="shrink-0 text-sm font-semibold text-slate-100">{value}</span>
    </div>
  );
}

function Status({ value }: { value: string }) {
  const good = ['COMPLETED', 'READY'].includes(value);
  const warn = ['APPROVAL_REQUIRED', 'REVIEW_REQUIRED', 'PARTIAL'].includes(value);
  const tone = good ? 'text-emerald-300 bg-emerald-500/10' : warn ? 'text-amber-300 bg-amber-500/10' : 'text-slate-300 bg-slate-700/40';
  return <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold ${tone}`}>{value}</span>;
}
