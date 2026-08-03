import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowDownRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  CircleDot,
  Clock3,
  FileCheck2,
  FileJson,
  FileText,
  Fingerprint,
  FileDown,
  GitBranch,
  History,
  Landmark,
  Link2,
  LockKeyhole,
  MessageSquareText,
  Scale,
  ShieldAlert,
  UserRound,
  UsersRound,
} from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge, { type BadgeVariant } from '../components/ui/Badge';
import { apiClient } from '../api/client';
import { useAppStore } from '../store/appStore';

interface Party { id: string; display_name?: string; role?: string; identifier_redacted?: string | null; }
interface Account { id: string; account_type?: string; status?: string; account_reference_redacted?: string | null; }
interface Communication { id: string; communication_type?: string; direction?: string; occurred_at?: string; subject_redacted?: string | null; }
interface Deadline { id: string; title?: string; deadline_type?: string; due_at?: string | null; calculation_status?: string; current_version?: number; timezone_name?: string; }
interface EvidenceNode { id: string; node_type?: string; title?: string; statement_redacted?: string | null; evidence_status?: string; review_status?: string; source_authority_id?: string | null; }
interface EvidenceLink { id: string; source_node_id?: string; target_node_id?: string; relationship_type?: string; confidence?: number; }
interface Finding { id: string; finding_type?: string; summary_redacted?: string; status?: string; node_id?: string | null; related_node_id?: string | null; }
interface Assessment { id: string; title?: string; assessment_type?: string; current_version?: number; review_status?: string; reviewer_role?: string | null; reviewed_at?: string | null; }
interface AuditEvent { id: string; action?: string; object_type?: string; created_at?: string; }
interface ListEnvelope<T> { items?: T[]; }

const empty = <T,>(value: ListEnvelope<T> | T[] | undefined): T[] => Array.isArray(value) ? value : value?.items ?? [];
const formatDate = (value?: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Not supplied';
const titleCase = (value?: string | null) => (value || 'unknown').toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const statusVariant = (status?: string): BadgeVariant => {
  const value = status?.toUpperCase() || '';
  if (value.includes('APPROVED') || value === 'PROVEN' || value === 'CALCULATED' || value === 'COMPLETE') return 'green';
  if (value.includes('CONFLICT') || value.includes('DISPUT') || value.includes('CONTRADICT') || value === 'REJECTED') return 'red';
  if (value.includes('MISSING') || value.includes('REVIEW') || value === 'OPEN') return 'amber';
  if (value === 'UNREVIEWED' || value === 'UNSUPPORTED') return 'purple';
  return 'slate';
};

async function fetchList<T>(path: string): Promise<T[]> {
  const response = await apiClient.get<ListEnvelope<T> | T[]>(path);
  return empty(response.data);
}

function SectionHeading({ icon: Icon, title, count, tone = 'text-gold' }: { icon: React.ElementType; title: string; count?: number; tone?: string }) {
  return <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-lg font-bold text-white"><Icon className={`h-5 w-5 ${tone}`} aria-hidden="true" />{title}</h2>{count !== undefined && <Badge variant="slate" size="sm">{count}</Badge>}</div>;
}

function EmptyPanel({ label, detail }: { label: string; detail: string }) {
  return <div className="border border-dashed border-slate-700 bg-slate-950/50 px-4 py-8 text-center"><CircleDot className="mx-auto h-6 w-6 text-slate-600" aria-hidden="true" /><p className="mt-3 text-sm font-medium text-slate-300">{label}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div>;
}

function Metric({ label, value, detail, icon: Icon, tone }: { label: string; value: number | string; detail: string; icon: React.ElementType; tone: string }) {
  return <div className="border border-slate-800 bg-slate-950/70 p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-black tabular-nums text-white">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div><Icon className={`h-5 w-5 ${tone}`} aria-hidden="true" /></div></div>;
}

export default function MatterWorkspace() {
  const { matterId = 'matter-1' } = useParams<{ matterId: string }>();
  const user = useAppStore((state) => state.user);
  const canReview = user?.role === 'attorney';
  const canExport = user?.role === 'attorney' || user?.role === 'admin';
  const [exportingFormat, setExportingFormat] = useState<'JSON' | 'PDF' | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const base = `/matters/${encodeURIComponent(matterId)}/intelligence`;
  const parties = useQuery({ queryKey: ['matter', matterId, 'parties'], queryFn: () => fetchList<Party>(`${base}/parties`) });
  const accounts = useQuery({ queryKey: ['matter', matterId, 'accounts'], queryFn: () => fetchList<Account>(`${base}/accounts`) });
  const communications = useQuery({ queryKey: ['matter', matterId, 'communications'], queryFn: () => fetchList<Communication>(`${base}/communications`) });
  const deadlines = useQuery({ queryKey: ['matter', matterId, 'deadlines'], queryFn: () => fetchList<Deadline>(`${base}/deadlines`) });
  const nodes = useQuery({ queryKey: ['matter', matterId, 'evidence-nodes'], queryFn: () => fetchList<EvidenceNode>(`${base}/evidence/nodes`) });
  const links = useQuery({ queryKey: ['matter', matterId, 'evidence-links'], queryFn: () => fetchList<EvidenceLink>(`${base}/evidence/links`) });
  const findings = useQuery({ queryKey: ['matter', matterId, 'evidence-findings'], queryFn: () => fetchList<Finding>(`${base}/evidence/findings`) });
  const assessments = useQuery({ queryKey: ['matter', matterId, 'assessments'], queryFn: () => fetchList<Assessment>(`${base}/assessments`) });
  const audit = useQuery({ queryKey: ['matter', matterId, 'audit-events'], queryFn: () => fetchList<AuditEvent>(`${base}/audit-events`) });

  const allQueries = [parties, accounts, communications, deadlines, nodes, links, findings, assessments, audit];
  const isLoading = allQueries.some((query) => query.isLoading);
  const hasError = allQueries.some((query) => query.isError);
  const chronology = useMemo(() => [
    ...communications.data?.map((item) => ({ date: item.occurred_at, label: item.subject_redacted || titleCase(item.communication_type), detail: `${titleCase(item.direction)} communication`, icon: MessageSquareText, tone: 'text-blue-400' })) || [],
    ...deadlines.data?.map((item) => ({ date: item.due_at, label: item.title || 'Untitled deadline', detail: `${titleCase(item.deadline_type)} deadline`, icon: CalendarClock, tone: 'text-amber-400' })) || [],
    ...audit.data?.map((item) => ({ date: item.created_at, label: titleCase(item.action), detail: item.object_type || 'Audit event', icon: History, tone: 'text-slate-400' })) || [],
  ].sort((a, b) => (new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime())), [communications.data, deadlines.data, audit.data]);
  const nodeById = useMemo(() => new Map((nodes.data || []).map((node) => [node.id, node])), [nodes.data]);  const exportMatter = async (format: 'JSON' | 'PDF') => {
    setExportingFormat(format);
    setExportError(null);
    try {
      const response = await apiClient.post<Blob>(`/matters/${encodeURIComponent(matterId)}/exports`, { format }, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: format === 'JSON' ? 'application/json' : 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `matter-${matterId}-export.${format.toLowerCase()}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError('The export could not be generated. Your authorization and the protected matter API were not changed.');
    } finally {
      setExportingFormat(null);
    }
  };

  return <main className="space-y-6" data-testid="matter-workspace">
    <header className="flex flex-col gap-4 border-b border-gold/20 pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div><div className="flex flex-wrap items-center gap-2"><Badge variant="blue" size="sm" dot>Persistent matter</Badge><Badge variant={canReview ? 'green' : 'amber'} size="sm">{canReview ? 'Attorney review access' : 'Read-only review posture'}</Badge></div><h1 className="mt-3 text-3xl font-black tracking-tight text-white">Matter workspace</h1><p className="mt-1 font-mono text-xs text-slate-500">{matterId}</p></div>
            <div className="flex flex-wrap items-center justify-end gap-2">
        <div className="flex items-center gap-2 border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-200"><LockKeyhole className="h-4 w-4" aria-hidden="true" /> Authorization is enforced by the API</div>
        {canExport && <div className="flex flex-wrap gap-2" aria-label="Matter export actions"><Button variant="outline" size="sm" icon={FileJson} loading={exportingFormat === 'JSON'} disabled={exportingFormat !== null} onClick={() => void exportMatter('JSON')}>JSON export</Button><Button variant="outline" size="sm" icon={FileDown} loading={exportingFormat === 'PDF'} disabled={exportingFormat !== null} onClick={() => void exportMatter('PDF')}>PDF export</Button></div>}
      </div>
    </header>
    <div className="border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-100" role="note"><ShieldAlert className="mr-2 inline h-4 w-4 text-amber-300" aria-hidden="true" />Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.</div>
    {exportError && <div className="border border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-200" role="alert">{exportError}</div>}
    {hasError && <div className="border border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-200" role="alert"><AlertTriangle className="mr-2 inline h-4 w-4" aria-hidden="true" />Some matter data could not be loaded. Protected API responses are not replaced with invented records.</div>}
    {isLoading && <div className="border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400" role="status"><Clock3 className="mr-2 inline h-4 w-4 animate-pulse" aria-hidden="true" />Loading matter records...</div>}

    <section className="grid grid-cols-2 gap-px border border-slate-800 bg-slate-800 md:grid-cols-4" aria-label="Matter summary">
      <Metric label="Parties" value={parties.data?.length || 0} detail="scoped records" icon={UsersRound} tone="text-blue-400" />
      <Metric label="Accounts" value={accounts.data?.length || 0} detail="creditor records" icon={Landmark} tone="text-gold" />
      <Metric label="Open deadlines" value={deadlines.data?.filter((item) => item.calculation_status !== 'COMPLETE').length || 0} detail="versioned dates" icon={CalendarClock} tone="text-amber-400" />
      <Metric label="Findings" value={findings.data?.filter((item) => item.status === 'OPEN').length || 0} detail="review queue" icon={ShieldAlert} tone="text-rose-400" />
    </section>

    <section className="grid gap-6 xl:grid-cols-[1.35fr_.85fr]">
      <div className="space-y-6">
        <Card padding="lg"><SectionHeading icon={UsersRound} title="Parties and accounts" count={(parties.data?.length || 0) + (accounts.data?.length || 0)} /><div className="mt-5 grid gap-3 md:grid-cols-2"><div className="space-y-2">{parties.data?.length ? parties.data.map((party) => <div key={party.id} className="flex items-center justify-between gap-3 border border-slate-800 bg-slate-950/60 p-3"><div className="flex min-w-0 items-center gap-3"><UserRound className="h-4 w-4 shrink-0 text-blue-400" aria-hidden="true" /><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-200">{party.display_name || 'Redacted party'}</p><p className="text-xs text-slate-500">{titleCase(party.role)}{party.identifier_redacted ? ` · ${party.identifier_redacted}` : ''}</p></div></div><Badge variant="slate" size="sm">Party</Badge></div>) : <EmptyPanel label="No parties returned" detail="Party records will appear when the protected matter API returns them." />}</div><div className="space-y-2">{accounts.data?.length ? accounts.data.map((account) => <div key={account.id} className="flex items-center justify-between gap-3 border border-slate-800 bg-slate-950/60 p-3"><div className="flex min-w-0 items-center gap-3"><Landmark className="h-4 w-4 shrink-0 text-gold" aria-hidden="true" /><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-200">{titleCase(account.account_type)}</p><p className="text-xs text-slate-500">{account.account_reference_redacted || 'Reference redacted'} · {titleCase(account.status)}</p></div></div><Badge variant={statusVariant(account.status)} size="sm">{titleCase(account.status)}</Badge></div>) : <EmptyPanel label="No accounts returned" detail="Creditor and servicer records remain scoped to this matter." />}</div></div></Card>

        <Card padding="lg"><SectionHeading icon={CalendarClock} title="Deadline calendar" count={deadlines.data?.length || 0} /><div className="mt-5 space-y-2">{deadlines.data?.length ? deadlines.data.map((deadline) => <div key={deadline.id} className="grid gap-3 border border-slate-800 bg-slate-950/60 p-3 md:grid-cols-[1fr_auto] md:items-center"><div><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-semibold text-slate-200">{deadline.title || 'Untitled deadline'}</p><Badge variant={statusVariant(deadline.calculation_status)} size="sm">{titleCase(deadline.calculation_status)}</Badge></div><p className="mt-1 text-xs text-slate-500">{titleCase(deadline.deadline_type)} · version {deadline.current_version || 1} · {deadline.timezone_name || 'Timezone not supplied'}</p></div><time className="text-sm font-semibold tabular-nums text-amber-200">{formatDate(deadline.due_at)}</time></div>) : <EmptyPanel label="No deadlines returned" detail="Calculated and human-review dates will appear here." />}</div></Card>

        <Card padding="lg"><SectionHeading icon={History} title="Chronology" count={chronology.length} /><div className="mt-5 space-y-3" aria-label="Matter chronology">{chronology.length ? chronology.map((event, index) => { const Icon = event.icon; return <div key={`${event.label}-${event.date || index}`} className="relative flex gap-3 border-l border-slate-700 pl-4"><span className="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-gold" aria-hidden="true" /><Icon className={`mt-0.5 h-4 w-4 shrink-0 ${event.tone}`} aria-hidden="true" /><div className="min-w-0"><div className="flex flex-wrap items-center gap-x-3 gap-y-1"><p className="text-sm font-semibold text-slate-200">{event.label}</p><time className="text-xs tabular-nums text-slate-500">{formatDate(event.date)}</time></div><p className="mt-1 text-xs text-slate-500">{event.detail}</p></div></div>; }) : <EmptyPanel label="Chronology is empty" detail="Communications, deadlines, and immutable audit events will appear here." />}</div></Card>
        <Card padding="lg"><SectionHeading icon={GitBranch} title="Evidence graph" count={(nodes.data?.length || 0) + (links.data?.length || 0)} /><div className="mt-5 grid gap-3 lg:grid-cols-2">{nodes.data?.length ? nodes.data.map((node) => <div key={node.id} className="border border-slate-800 bg-slate-950/60 p-4"><div className="flex items-start justify-between gap-3"><div className="flex min-w-0 items-center gap-2"><CircleDot className="h-4 w-4 shrink-0 text-blue-400" aria-hidden="true" /><h3 className="truncate text-sm font-semibold text-slate-200">{node.title || 'Untitled evidence'}</h3></div><Badge variant={statusVariant(node.evidence_status)} size="sm">{titleCase(node.evidence_status)}</Badge></div><p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">{node.statement_redacted || 'Redacted or missing statement.'}</p><div className="mt-3 flex flex-wrap gap-2"><Badge variant="slate" size="sm">{titleCase(node.node_type)}</Badge>{node.source_authority_id && <Badge variant="blue" size="sm">{node.source_authority_id}</Badge>}</div></div>) : <EmptyPanel label="Evidence graph is empty" detail="Claims, facts, documents, and authorities will appear as graph nodes." />}</div><div className="mt-4 space-y-2">{links.data?.length ? links.data.map((link) => <div key={link.id} className="flex items-center gap-2 border-l-2 border-blue-500/40 px-3 py-2 text-xs"><span className="truncate text-slate-300">{nodeById.get(link.source_node_id || '')?.title || 'Unknown source'}</span><ArrowDownRight className="h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden="true" /><span className="truncate text-slate-300">{nodeById.get(link.target_node_id || '')?.title || 'Unknown target'}</span><Badge variant={link.relationship_type === 'CONTRADICTS' ? 'red' : 'blue'} size="sm">{titleCase(link.relationship_type)}</Badge></div>) : <p className="text-xs text-slate-600">No graph relationships returned.</p>}</div></Card>
      </div>

      <aside className="space-y-6">
        <Card padding="lg"><SectionHeading icon={ShieldAlert} title="Contradictions and missing evidence" count={findings.data?.length || 0} /><div className="mt-5 space-y-2">{findings.data?.length ? findings.data.map((finding) => <div key={finding.id} className="border border-rose-500/20 bg-rose-500/5 p-3"><div className="flex items-center justify-between gap-2"><Badge variant={finding.finding_type === 'CONTRADICTORY_EVIDENCE' ? 'red' : 'amber'} size="sm">{titleCase(finding.finding_type)}</Badge><span className="text-[10px] uppercase tracking-wider text-slate-500">{titleCase(finding.status)}</span></div><p className="mt-2 text-sm text-rose-100">{finding.summary_redacted || 'Finding requires review.'}</p></div>) : <EmptyPanel label="No open findings" detail="Contradictions and missing evidence will be surfaced here." />}</div></Card>

        <Card padding="lg"><SectionHeading icon={FileCheck2} title="Assessment history" count={assessments.data?.length || 0} /><div className="mt-5 space-y-2">{assessments.data?.length ? assessments.data.map((assessment) => <div key={assessment.id} className="border border-slate-800 bg-slate-950/60 p-3"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-200">{assessment.title || 'Untitled assessment'}</p><p className="mt-1 text-xs text-slate-500">{titleCase(assessment.assessment_type)} · version {assessment.current_version || 1}</p></div><Badge variant={statusVariant(assessment.review_status)} size="sm">{titleCase(assessment.review_status)}</Badge></div><div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span>{assessment.reviewer_role ? `Reviewed by ${titleCase(assessment.reviewer_role)}` : canReview ? 'Attorney review available' : 'Professional review required'}</span>{assessment.reviewed_at && <time>{formatDate(assessment.reviewed_at)}</time>}</div></div>) : <EmptyPanel label="No assessments returned" detail="Versioned legal assessments will appear here." />}</div></Card>

        <Card padding="lg"><SectionHeading icon={History} title="Audit history" count={audit.data?.length || 0} /><div className="mt-5 space-y-3">{audit.data?.length ? audit.data.slice(0, 8).map((event) => <div key={event.id} className="flex gap-3 border-l border-slate-700 pl-3"><History className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" /><div><p className="text-sm text-slate-300">{titleCase(event.action)}</p><p className="mt-1 text-xs text-slate-500">{event.object_type || 'Matter object'} · {formatDate(event.created_at)}</p></div></div>) : <EmptyPanel label="No audit events returned" detail="Matter changes will appear in the immutable audit history." />}</div></Card>

        <Card padding="md" className="border-amber-500/30"><p className="flex items-center gap-2 text-sm font-semibold text-amber-200"><Scale className="h-4 w-4" aria-hidden="true" /> Provenance posture</p><p className="mt-2 text-xs leading-5 text-slate-400">Deadline calculations retain rule and authority references. Evidence previews remain redacted and should be reviewed against source documents.</p><div className="mt-3 flex flex-wrap gap-2"><Badge variant="green" size="sm"><Fingerprint className="h-3 w-3" aria-hidden="true" /> Tenant scoped</Badge><Badge variant="blue" size="sm"><Link2 className="h-3 w-3" aria-hidden="true" /> Provenance linked</Badge></div></Card>
      </aside>
    </section>
  </main>;
}
