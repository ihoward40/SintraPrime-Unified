import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Archive, BadgeCheck, BookOpen, CalendarClock, CheckCircle2, ClipboardCheck, ExternalLink, FileWarning, Filter, Gavel, Landmark, Layers3, Library, Loader2, LockKeyhole, Scale, Search, ShieldAlert, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';
import Badge, { type BadgeVariant } from '../components/ui/Badge';
import Card from '../components/ui/Card';

const LEGAL_WARNING = 'Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.';

type Domain = 'trust_law' | 'creditor_protection' | 'ucc' | 'bankruptcy_overlay';
type QueueType = 'pending_rule' | 'conflict' | 'stale_authority' | 'challenge';

interface CoverageData { jurisdictionName: string; supportStatus: string; domains: string[]; topicsCovered: number; rulesEncoded: number; authoritiesVerified: number; rulesRequiringReview: number; conflicts: number; staleAuthorities: number; productionEligible: number; knownLimitations: string[]; lastUpdated?: string; }
interface RuleRecord { id: string; domain: Domain; topic: string; statement: string; citations: string[]; authorityIds: string[]; authorityClassification: string; effectiveDate?: string; verificationStatus: string; humanReviewStatus: string; exceptions: string[]; limitations: string[]; conflictStatus: string; reviewStatus: string; sourceUrl?: string; }
interface AuthorityRecord { id: string; title: string; issuingBody: string; sourceClass: string; citation: string; effectiveDate?: string; verificationStatus: string; linkedRules: string[]; limitations: string[]; lastVerifiedDate?: string; sourceUrl?: string; }
interface ReviewQueueItem { id: string; label: string; type: QueueType; status: string; owner: string; due: string; reason: string; authorizationRequired: string; }
interface WorkspaceData { coverage: CoverageData; rules: RuleRecord[]; authorities: AuthorityRecord[]; reviewQueue: ReviewQueueItem[]; usedFallback: boolean; }

const fallbackAuthorities: AuthorityRecord[] = [
  { id: 'NJ-UTC-2015-276', title: 'New Jersey Uniform Trust Code', issuingBody: 'New Jersey Legislature', sourceClass: 'PRIMARY_LEGAL_AUTHORITY', citation: 'N.J.S.A. 3B:31-1 et seq.', effectiveDate: '2016-07-17', verificationStatus: 'PRIMARY_SOURCE_VERIFIED', linkedRules: ['NJ-TRUST-CERTIFICATION', 'NJ-TRUST-REPORTING', 'NJ-TRUST-MODIFICATION'], limitations: ['Attorney review is required before production use.', 'Rule summaries do not replace full statutory text.'], lastVerifiedDate: '2026-08-03', sourceUrl: '/legal-authorities/NJ-UTC-2015-276' },
  { id: 'NJ-UCC-12A-9', title: 'New Jersey Uniform Commercial Code Article 9', issuingBody: 'New Jersey Legislature', sourceClass: 'PRIMARY_LEGAL_AUTHORITY', citation: 'N.J.S.A. 12A:9-101 et seq.', effectiveDate: '2001-07-01', verificationStatus: 'PRIMARY_SOURCE_VERIFIED', linkedRules: ['NJ-UCC-CONTINUATION', 'NJ-UCC-TRUST-DEBTOR-NAME'], limitations: ['Administrative rule N.J.A.C. 17:33 remains locator-limited pending official verification.'], lastVerifiedDate: '2026-08-03', sourceUrl: '/legal-authorities/NJ-UCC-12A-9' },
  { id: 'FED-BANKRUPTCY-11USC541', title: 'Bankruptcy Estate and Spendthrift Interface', issuingBody: 'United States Congress', sourceClass: 'PRIMARY_LEGAL_AUTHORITY', citation: '11 U.S.C. 541', effectiveDate: '1978-11-06', verificationStatus: 'PRIMARY_SOURCE_LOCATED', linkedRules: ['NJ-BANKRUPTCY-SPENDTHRIFT-ISSUE-SPOT'], limitations: ['Bankruptcy overlays are issue-spotting only and require federal bankruptcy review.'], lastVerifiedDate: '2026-08-03', sourceUrl: '/legal-authorities/FED-BANKRUPTCY-11USC541' },
];

const fallbackRules: RuleRecord[] = [
  { id: 'NJ-TRUST-CERTIFICATION', domain: 'trust_law', topic: 'Certification of trust', statement: 'A trustee may provide a statutory certification of trust instead of the full trust instrument when New Jersey UTC conditions are satisfied.', citations: ['N.J.S.A. 3B:31-81'], authorityIds: ['NJ-UTC-2015-276'], authorityClassification: 'PRIMARY_LEGAL_AUTHORITY', effectiveDate: '2016-07-17', verificationStatus: 'PRIMARY_SOURCE_VERIFIED', humanReviewStatus: 'HUMAN_REVIEW_REQUIRED', exceptions: ['Recipient may request excerpts designating trustee powers.'], limitations: ['Does not determine whether a specific institution must accept the certification.'], conflictStatus: 'No open conflict recorded', reviewStatus: 'NOT_SUBMITTED', sourceUrl: '/legal-authorities/NJ-UTC-2015-276' },
  { id: 'NJ-TRUST-REPORTING', domain: 'trust_law', topic: 'Trustee reporting and records', statement: 'Trustees must keep adequate records and provide beneficiary information consistent with New Jersey UTC duties and notice limits.', citations: ['N.J.S.A. 3B:31-66', 'N.J.S.A. 3B:31-67'], authorityIds: ['NJ-UTC-2015-276'], authorityClassification: 'PRIMARY_LEGAL_AUTHORITY', effectiveDate: '2016-07-17', verificationStatus: 'PRIMARY_SOURCE_VERIFIED', humanReviewStatus: 'HUMAN_REVIEW_REQUIRED', exceptions: ['Duties may vary by trust terms where the UTC permits variation.'], limitations: ['Professional review required before relying on notice timing in client-facing output.'], conflictStatus: 'No open conflict recorded', reviewStatus: 'IN_REVIEW', sourceUrl: '/legal-authorities/NJ-UTC-2015-276' },
  { id: 'NJ-CREDITOR-WAGE-EXECUTION', domain: 'creditor_protection', topic: 'Wage execution limits', statement: 'New Jersey wage execution is limited by state statutory caps and must be distinguished from federal and support-order garnishment overlays.', citations: ['N.J.S.A. 2A:17-56'], authorityIds: ['NJ-EXEC-WAGE-2A17-56'], authorityClassification: 'PRIMARY_LEGAL_AUTHORITY', effectiveDate: '1951-12-01', verificationStatus: 'PRIMARY_SOURCE_LOCATED', humanReviewStatus: 'HUMAN_REVIEW_REQUIRED', exceptions: ['Support, tax, and government claims may follow separate authority.'], limitations: ['Issue-spotting only; do not calculate disposable earnings without current payroll facts.'], conflictStatus: 'No open conflict recorded', reviewStatus: 'CHANGES_REQUESTED', sourceUrl: '/legal-authorities/NJ-EXEC-WAGE-2A17-56' },
  { id: 'NJ-UCC-CONTINUATION', domain: 'ucc', topic: 'Continuation window and lapse', statement: 'A UCC continuation statement must be filed in the statutory window before lapse; late continuation cannot revive a lapsed financing statement.', citations: ['N.J.S.A. 12A:9-515'], authorityIds: ['NJ-UCC-12A-9'], authorityClassification: 'PRIMARY_LEGAL_AUTHORITY', effectiveDate: '2001-07-01', verificationStatus: 'PRIMARY_SOURCE_VERIFIED', humanReviewStatus: 'HUMAN_REVIEW_REQUIRED', exceptions: ['Manufactured-home and public-finance filings may follow special durations.'], limitations: ['Administrative filing-office practice depends on official N.J.A.C. 17:33 verification.'], conflictStatus: 'N.J.A.C. 17:33 source limitation disclosed', reviewStatus: 'NOT_SUBMITTED', sourceUrl: '/legal-authorities/NJ-UCC-12A-9' },
  { id: 'NJ-BANKRUPTCY-SPENDTHRIFT-ISSUE-SPOT', domain: 'bankruptcy_overlay', topic: 'Spendthrift exclusion and estate property', statement: 'Potential bankruptcy treatment of trust interests is flagged for federal bankruptcy review and is not presented as filing advice.', citations: ['11 U.S.C. 541(c)(2)'], authorityIds: ['FED-BANKRUPTCY-11USC541'], authorityClassification: 'PRIMARY_LEGAL_AUTHORITY', effectiveDate: '1978-11-06', verificationStatus: 'PRIMARY_SOURCE_LOCATED', humanReviewStatus: 'FEDERAL_BANKRUPTCY_REVIEW_REQUIRED', exceptions: ['Self-settled, revocable, and fraudulent-transfer facts require separate review.'], limitations: ['Does not provide bankruptcy filing advice or debtor representation.'], conflictStatus: 'Federal overlay review required', reviewStatus: 'NOT_SUBMITTED', sourceUrl: '/legal-authorities/FED-BANKRUPTCY-11USC541' },
];

const fallbackCoverage: CoverageData = { jurisdictionName: 'New Jersey', supportStatus: 'TESTED - non-production pilot', domains: ['Trust law', 'Creditor protection', 'UCC filing', 'Bankruptcy overlay'], topicsCovered: 47, rulesEncoded: fallbackRules.length, authoritiesVerified: 2, rulesRequiringReview: fallbackRules.length, conflicts: 1, staleAuthorities: 1, productionEligible: 0, knownLimitations: ['No New Jersey rule is production eligible without licensed-attorney approval.', 'Bankruptcy rules are federal issue-spotting only.', 'N.J.A.C. 17:33 administrative filing rules require official-source verification before production use.'], lastUpdated: '2026-08-03' };
const fallbackReviewQueue: ReviewQueueItem[] = [
  { id: 'RQ-NJ-001', label: 'Wage execution and protected-benefit interaction', type: 'pending_rule', status: 'SUBMITTED', owner: 'Licensed attorney required', due: 'Before production eligibility', reason: 'Primary authority located; calculation and exception handling require legal review.', authorizationRequired: 'LICENSED_ATTORNEY' },
  { id: 'RQ-NJ-002', label: 'N.J.A.C. 17:33 filing-office source verification', type: 'stale_authority', status: 'HUMAN_REVIEW_REQUIRED', owner: 'Legal researcher', due: 'Next source-refresh cycle', reason: 'Locator copy is available, but official current administrative text has not been verified in-app.', authorizationRequired: 'LEGAL_RESEARCHER' },
  { id: 'RQ-NJ-003', label: 'Bankruptcy spendthrift issue-spotting boundary', type: 'conflict', status: 'FEDERAL_BANKRUPTCY_REVIEW_REQUIRED', owner: 'Bankruptcy counsel', due: 'Before client-facing representation', reason: 'State trust rule intersects federal estate-property analysis.', authorizationRequired: 'LICENSED_ATTORNEY' },
];

const domainLabels: Record<Domain, string> = { trust_law: 'Trust law', creditor_protection: 'Creditor protection', ucc: 'UCC', bankruptcy_overlay: 'Bankruptcy overlay' };
const domainIcons: Record<Domain, React.ElementType> = { trust_law: BookOpen, creditor_protection: ShieldCheck, ucc: Archive, bankruptcy_overlay: ShieldAlert };
const queueTypeLabels: Record<QueueType, string> = { pending_rule: 'Rule review', conflict: 'Conflict', stale_authority: 'Stale source', challenge: 'Challenge' };

function asObject(value: unknown): Record<string, unknown> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function asText(value: unknown, fallback = ''): string { return typeof value === 'string' && value.trim() ? value : fallback; }
function asNumber(value: unknown, fallback = 0): number { return typeof value === 'number' && Number.isFinite(value) ? value : fallback; }
function asList(value: unknown): string[] { return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []; }
async function safeJson<T>(url: string): Promise<T | null> { try { const response = await fetch(url, { headers: { Accept: 'application/json' } }); return response.ok ? await response.json() as T : null; } catch { return null; } }
function normalizeDomain(value: unknown): Domain { const text = String(value || '').toLowerCase().replace(/[-\s]/g, '_'); if (text.includes('creditor')) return 'creditor_protection'; if (text.includes('ucc') || text.includes('filing')) return 'ucc'; if (text.includes('bankruptcy')) return 'bankruptcy_overlay'; return 'trust_law'; }
function statusVariant(status: string): BadgeVariant { const value = status.toUpperCase(); if (value.includes('PRODUCTION') || value.includes('APPROVED')) return 'green'; if (value.includes('CONFLICT') || value.includes('CHANGES') || value.includes('REJECT')) return 'red'; if (value.includes('REVIEW') || value.includes('SUBMITTED') || value.includes('LOCATED')) return 'amber'; if (value.includes('VERIFIED') || value.includes('TESTED')) return 'blue'; return 'slate'; }
function formatStatus(status: string): string { return status.replace(/_/g, ' ').replace(/\s+/g, ' ').trim(); }
function normalizeCoverage(payload: unknown): CoverageData {
  const obj = asObject(asObject(payload).coverage ?? payload);
  return {
    jurisdictionName: asText(obj.jurisdiction_name ?? obj.name, fallbackCoverage.jurisdictionName),
    supportStatus: asText(obj.status ?? obj.support_status ?? obj.coverage_status, fallbackCoverage.supportStatus),
    domains: asList(obj.domains ?? obj.researched_domains).length ? asList(obj.domains ?? obj.researched_domains) : fallbackCoverage.domains,
    topicsCovered: asNumber(obj.topics_covered, fallbackCoverage.topicsCovered),
    rulesEncoded: asNumber(obj.rules_encoded ?? obj.rule_count, fallbackCoverage.rulesEncoded),
    authoritiesVerified: asNumber(obj.authorities_verified ?? obj.verified_authorities, fallbackCoverage.authoritiesVerified),
    rulesRequiringReview: asNumber(obj.rules_requiring_review ?? obj.human_review_required_count, fallbackCoverage.rulesRequiringReview),
    conflicts: asNumber(obj.conflicts ?? obj.open_conflicts, fallbackCoverage.conflicts),
    staleAuthorities: asNumber(obj.stale_authorities, fallbackCoverage.staleAuthorities),
    productionEligible: asNumber(obj.production_eligible_count ?? obj.production_eligible, 0),
    knownLimitations: asList(obj.known_limitations ?? obj.limitations).length ? asList(obj.known_limitations ?? obj.limitations) : fallbackCoverage.knownLimitations,
    lastUpdated: asText(obj.updated_at ?? obj.last_updated, fallbackCoverage.lastUpdated),
  };
}

function normalizeRule(item: unknown): RuleRecord {
  const obj = asObject(item);
  return {
    id: asText(obj.id ?? obj.rule_id, 'unidentified-rule'),
    domain: normalizeDomain(obj.domain),
    topic: asText(obj.topic, 'Unlabeled topic'),
    statement: asText(obj.rule_statement ?? obj.statement ?? obj.summary, 'Rule statement unavailable.'),
    citations: asList(obj.citations ?? obj.citation),
    authorityIds: asList(obj.authority_ids ?? obj.authorities),
    authorityClassification: asText(obj.authority_classification ?? obj.source_classification, 'PRIMARY_LEGAL_AUTHORITY'),
    effectiveDate: asText(obj.effective_from ?? obj.effective_date),
    verificationStatus: asText(obj.verification_status, 'HUMAN_REVIEW_REQUIRED'),
    humanReviewStatus: asText(obj.human_review_status ?? (obj.requires_human_review ? 'HUMAN_REVIEW_REQUIRED' : ''), 'HUMAN_REVIEW_REQUIRED'),
    exceptions: Array.isArray(obj.exceptions) ? obj.exceptions.map((entry) => typeof entry === 'string' ? entry : JSON.stringify(entry)).filter(Boolean) : [],
    limitations: asList(obj.limitations),
    conflictStatus: asList(obj.conflicting_rule_ids).length ? 'Open conflict recorded' : asText(obj.conflict_status, 'No open conflict recorded'),
    reviewStatus: asText(obj.review_status ?? obj.status, 'NOT_SUBMITTED'),
    sourceUrl: asText(obj.source_url),
  };
}

function normalizeAuthority(item: unknown): AuthorityRecord {
  const obj = asObject(item);
  return {
    id: asText(obj.id ?? obj.authority_id, 'unidentified-authority'),
    title: asText(obj.title, 'Authority title unavailable'),
    issuingBody: asText(obj.issuing_body ?? obj.court_or_agency ?? obj.courtOrAgency, 'Issuing body unavailable'),
    sourceClass: asText(obj.source_classification ?? obj.source_class, 'UNKNOWN'),
    citation: asText(obj.citation, 'Citation unavailable'),
    effectiveDate: asText(obj.effective_date ?? obj.effective_from),
    verificationStatus: asText(obj.verification_status, 'UNVERIFIED'),
    linkedRules: asList(obj.linked_rules ?? obj.rule_ids),
    limitations: asList(obj.limitations),
    lastVerifiedDate: asText(obj.last_verified_at ?? obj.last_verified_date),
    sourceUrl: asText(obj.source_url),
  };
}

function normalizeQueueItem(item: unknown): ReviewQueueItem {
  const obj = asObject(item);
  const rawType = asText(obj.type ?? obj.queue_type, 'pending_rule');
  const type: QueueType = rawType === 'conflict' || rawType === 'stale_authority' || rawType === 'challenge' ? rawType : 'pending_rule';
  return {
    id: asText(obj.id ?? obj.queue_id, 'review-item'),
    label: asText(obj.label ?? obj.title ?? obj.object_id, 'Review item'),
    type,
    status: asText(obj.status ?? obj.review_status, 'SUBMITTED'),
    owner: asText(obj.owner ?? obj.assignee, 'Unassigned'),
    due: asText(obj.due ?? obj.due_at, 'Not scheduled'),
    reason: asText(obj.reason ?? obj.findings, 'Review required before production eligibility.'),
    authorizationRequired: asText(obj.authorization_required ?? obj.reviewer_role, 'LICENSED_ATTORNEY'),
  };
}

async function loadWorkspace(): Promise<WorkspaceData> {
  const [coveragePayload, rulesPayload, queuePayload] = await Promise.all([
    safeJson('/jurisdictions/NJ/coverage'),
    safeJson('/jurisdictions/NJ/rules'),
    safeJson('/jurisdictions/NJ/review-queue'),
  ]);
  const rawRules = Array.isArray(rulesPayload) ? rulesPayload : Array.isArray(asObject(rulesPayload).rules) ? asObject(rulesPayload).rules as unknown[] : [];
  const rules = rawRules.map(normalizeRule);
  const authorityIds = Array.from(new Set(rules.flatMap((rule) => rule.authorityIds))).filter(Boolean);
  const authorityResponses = await Promise.all(authorityIds.slice(0, 12).map((id) => safeJson(`/legal-authorities/${id}`)));
  const authorities = authorityResponses.filter(Boolean).map(normalizeAuthority);
  const rawQueue = Array.isArray(queuePayload) ? queuePayload : Array.isArray(asObject(queuePayload).items) ? asObject(queuePayload).items as unknown[] : [];
  const usefulApiData = Boolean(coveragePayload) || rules.length > 0 || rawQueue.length > 0;
  return {
    coverage: coveragePayload ? normalizeCoverage(coveragePayload) : fallbackCoverage,
    rules: rules.length ? rules : fallbackRules,
    authorities: authorities.length ? authorities : fallbackAuthorities,
    reviewQueue: rawQueue.length ? rawQueue.map(normalizeQueueItem) : fallbackReviewQueue,
    usedFallback: !usefulApiData,
  };
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/50 p-8 text-center"><FileWarning className="mx-auto h-8 w-8 text-slate-500" aria-hidden="true" /><h3 className="mt-3 text-base font-semibold text-white">{title}</h3><p className="mx-auto mt-2 max-w-lg text-sm text-slate-500">{detail}</p></div>;
}

function MetricCard({ label, value, detail, icon: Icon, variant }: { label: string; value: string | number; detail: string; icon: React.ElementType; variant: BadgeVariant }) {
  return <Card padding="md" className="min-h-[132px] rounded-lg"><div className="flex items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 text-3xl font-black text-white">{value}</p></div><span className="rounded-lg border border-slate-700 bg-slate-950/80 p-2 text-slate-300"><Icon className="h-5 w-5" aria-hidden="true" /></span></div><Badge variant={variant} size="sm" className="mt-4">{detail}</Badge></Card>;
}

function RuleCard({ rule, onAuthority }: { rule: RuleRecord; onAuthority: (id: string) => void }) {
  const DomainIcon = domainIcons[rule.domain];
  return <article className="rounded-lg border border-slate-800 bg-slate-950/80 p-4 focus-within:ring-2 focus-within:ring-gold/50"><div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge variant="blue" size="sm"><DomainIcon className="h-3.5 w-3.5" aria-hidden="true" /> {domainLabels[rule.domain]}</Badge><Badge variant={statusVariant(rule.humanReviewStatus)} size="sm">{formatStatus(rule.humanReviewStatus)}</Badge><Badge variant={statusVariant(rule.reviewStatus)} size="sm">Review: {formatStatus(rule.reviewStatus)}</Badge></div><h3 className="mt-3 text-lg font-bold text-white">{rule.topic}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{rule.statement}</p></div><span className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[10px] font-mono text-slate-400">{rule.id}</span></div><dl className="mt-4 grid gap-3 text-sm md:grid-cols-3"><div><dt className="text-xs uppercase tracking-wider text-slate-500">Citation</dt><dd className="mt-1 text-slate-200">{rule.citations.join('; ') || 'Citation pending'}</dd></div><div><dt className="text-xs uppercase tracking-wider text-slate-500">Authority class</dt><dd className="mt-1 text-slate-200">{formatStatus(rule.authorityClassification)}</dd></div><div><dt className="text-xs uppercase tracking-wider text-slate-500">Effective date</dt><dd className="mt-1 text-slate-200">{rule.effectiveDate || 'Human review required'}</dd></div></dl><div className="mt-4 grid gap-3 lg:grid-cols-2"><div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Exceptions</p><ul className="mt-2 space-y-1 text-sm text-slate-300">{(rule.exceptions.length ? rule.exceptions : ['No encoded exception list.']).map((item) => <li key={item}>- {item}</li>)}</ul></div><div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Limitations and conflicts</p><p className="mt-2 text-sm text-slate-300">{rule.conflictStatus}</p><ul className="mt-2 space-y-1 text-sm text-slate-300">{(rule.limitations.length ? rule.limitations : ['No limitation text supplied by the API.']).map((item) => <li key={item}>- {item}</li>)}</ul></div></div><div className="mt-4 flex flex-wrap items-center gap-2">{rule.authorityIds.map((authorityId) => <button key={authorityId} type="button" className="rounded-md border border-gold/30 bg-gold/5 px-2 py-1 text-xs text-gold transition hover:bg-gold/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60" onClick={() => onAuthority(authorityId)}>View authority {authorityId}</button>)}{rule.sourceUrl && <a href={rule.sourceUrl} className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60">Source <ExternalLink className="h-3 w-3" aria-hidden="true" /></a>}</div></article>;
}
export default function NewJerseyJurisdiction() {
  const [data, setData] = useState<WorkspaceData>({ coverage: fallbackCoverage, rules: fallbackRules, authorities: fallbackAuthorities, reviewQueue: fallbackReviewQueue, usedFallback: true });
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState<'all' | Domain>('all');
  const [verification, setVerification] = useState('all');
  const [review, setReview] = useState('all');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [selectedAuthorityId, setSelectedAuthorityId] = useState(fallbackAuthorities[0].id);
  const [authorizedQueueVisible, setAuthorizedQueueVisible] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoadState('loading');
    loadWorkspace().then((workspace) => { if (!mounted) return; setData(workspace); setSelectedAuthorityId(workspace.authorities[0]?.id ?? fallbackAuthorities[0].id); setLoadState('ready'); }).catch(() => { if (!mounted) return; setData({ coverage: fallbackCoverage, rules: fallbackRules, authorities: fallbackAuthorities, reviewQueue: fallbackReviewQueue, usedFallback: true }); setLoadState('error'); });
    return () => { mounted = false; };
  }, []);

  const verificationOptions = useMemo(() => ['all', ...Array.from(new Set(data.rules.map((rule) => rule.verificationStatus)))], [data.rules]);
  const reviewOptions = useMemo(() => ['all', ...Array.from(new Set(data.rules.map((rule) => rule.humanReviewStatus)))], [data.rules]);
  const filteredRules = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return data.rules.filter((rule) => {
      const matchesQuery = !needle || [rule.id, rule.topic, rule.statement, ...rule.citations, ...rule.authorityIds].join(' ').toLowerCase().includes(needle);
      return (domain === 'all' || rule.domain === domain) && (verification === 'all' || rule.verificationStatus === verification) && (review === 'all' || rule.humanReviewStatus === review) && (!effectiveDate || !rule.effectiveDate || rule.effectiveDate <= effectiveDate) && matchesQuery;
    });
  }, [data.rules, domain, effectiveDate, query, review, verification]);
  const selectedAuthority = data.authorities.find((authority) => authority.id === selectedAuthorityId) ?? data.authorities[0];

  return (
    <section className="space-y-6" aria-labelledby="new-jersey-workspace-title">
      <div className="rounded-lg border border-gold/25 bg-slate-950/80 p-5 md:p-6">
        <div className="grid gap-5 xl:grid-cols-[1.3fr_.7fr] xl:items-end">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-gold">Jurisdiction Workspace</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 id="new-jersey-workspace-title" className="text-3xl font-black text-white md:text-4xl">New Jersey Trust Intelligence</h1>
              <Badge variant={statusVariant(data.coverage.supportStatus)}>{formatStatus(data.coverage.supportStatus)}</Badge>
            </div>
            <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">{LEGAL_WARNING}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4 xl:grid-cols-2">
            {[['Conflicts', data.coverage.conflicts], ['Stale sources', data.coverage.staleAuthorities], ['Topics', data.coverage.topicsCovered], ['Updated', data.coverage.lastUpdated ?? 'Unknown']].map(([label, value]) => <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 text-xl font-bold text-white">{value}</p></div>)}
          </div>
        </div>
        {data.usedFallback && <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-sm text-amber-200" role="status"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />API data is unavailable in this frontend session, so static pilot data is displayed with the same review warnings.</div>}
        {loadState === 'loading' && <div className="mt-4 flex items-center gap-2 text-sm text-slate-400" role="status"><Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading New Jersey jurisdiction data...</div>}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Coverage overview metrics">
        <MetricCard label="Rules encoded" value={data.coverage.rulesEncoded} detail="pilot rule set" icon={Layers3} variant="blue" />
        <MetricCard label="Verified authorities" value={data.coverage.authoritiesVerified} detail="primary-source weighted" icon={Library} variant="green" />
        <MetricCard label="Require review" value={data.coverage.rulesRequiringReview} detail="licensed review gate" icon={ClipboardCheck} variant="amber" />
        <MetricCard label="Production eligible" value={data.coverage.productionEligible} detail="must remain zero" icon={LockKeyhole} variant="red" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.45fr_.85fr]">
        <div className="space-y-6">
          <Card padding="lg" className="rounded-lg">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div><h2 className="flex items-center gap-2 text-xl font-bold text-white"><Scale className="h-5 w-5 text-gold" aria-hidden="true" /> Coverage Overview</h2><p className="mt-2 text-sm text-slate-400">Domains, limitations, and gate posture for the New Jersey pilot.</p></div><div className="flex flex-wrap gap-2">{data.coverage.domains.map((coveredDomain) => <Badge key={coveredDomain} variant="blue" size="sm">{coveredDomain}</Badge>)}</div></div>
            <div className="mt-5 grid gap-3 lg:grid-cols-3">{data.coverage.knownLimitations.map((limitation) => <div key={limitation} className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-100"><span className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-300"><AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> Limitation</span><p>{limitation}</p></div>)}</div>
          </Card>

          <Card padding="lg" className="rounded-lg" gold>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><h2 className="flex items-center gap-2 text-xl font-bold text-white"><Filter className="h-5 w-5 text-gold" aria-hidden="true" /> Rule Explorer</h2><p className="mt-2 text-sm text-slate-400">Filter legal rules by domain, source posture, review requirement, and effective date.</p></div><Badge variant="amber">{filteredRules.length} visible rules</Badge></div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <label className="md:col-span-2 xl:col-span-2"><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Search</span><div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" /><input className="input-dark pl-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rule, topic, citation, authority ID" /></div></label>
              <label><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Domain</span><select className="input-dark" value={domain} onChange={(event) => setDomain(event.target.value as 'all' | Domain)}><option value="all">All domains</option>{Object.entries(domainLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Effective on</span><input className="input-dark" type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} /></label>
              <label><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Review</span><select className="input-dark" value={review} onChange={(event) => setReview(event.target.value)}>{reviewOptions.map((option) => <option key={option} value={option}>{option === 'all' ? 'All review states' : formatStatus(option)}</option>)}</select></label>
              <label className="md:col-span-2 xl:col-span-2"><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Verification</span><select className="input-dark" value={verification} onChange={(event) => setVerification(event.target.value)}>{verificationOptions.map((option) => <option key={option} value={option}>{option === 'all' ? 'All verification states' : formatStatus(option)}</option>)}</select></label>
            </div>
            <div className="mt-5 space-y-3">{filteredRules.length === 0 ? <EmptyState title="No rules match the current filters" detail="Adjust the domain, verification, review, effective-date, or search filters to broaden the rule set." /> : filteredRules.map((rule) => <RuleCard key={rule.id} rule={rule} onAuthority={setSelectedAuthorityId} />)}</div>
          </Card>
        </div>

        <aside className="space-y-6">
          <Card padding="lg" className="rounded-lg">
            <h2 className="flex items-center gap-2 text-xl font-bold text-white"><Landmark className="h-5 w-5 text-gold" aria-hidden="true" /> Authority Viewer</h2>
            <label className="mt-4 block"><span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Authority</span><select className="input-dark" value={selectedAuthorityId} onChange={(event) => setSelectedAuthorityId(event.target.value)}>{data.authorities.map((authority) => <option key={authority.id} value={authority.id}>{authority.citation} - {authority.title}</option>)}</select></label>
            {selectedAuthority ? <div className="mt-5 space-y-4"><div><Badge variant={statusVariant(selectedAuthority.verificationStatus)}>{formatStatus(selectedAuthority.verificationStatus)}</Badge><h3 className="mt-3 text-lg font-bold text-white">{selectedAuthority.title}</h3><p className="mt-1 text-sm text-slate-400">{selectedAuthority.issuingBody}</p></div><dl className="space-y-3 text-sm"><div><dt className="text-xs uppercase tracking-wider text-slate-500">Citation</dt><dd className="mt-1 text-slate-200">{selectedAuthority.citation}</dd></div><div><dt className="text-xs uppercase tracking-wider text-slate-500">Source class</dt><dd className="mt-1 text-slate-200">{formatStatus(selectedAuthority.sourceClass)}</dd></div><div><dt className="text-xs uppercase tracking-wider text-slate-500">Effective date</dt><dd className="mt-1 text-slate-200">{selectedAuthority.effectiveDate || 'Not supplied'}</dd></div><div><dt className="text-xs uppercase tracking-wider text-slate-500">Last verified</dt><dd className="mt-1 text-slate-200">{selectedAuthority.lastVerifiedDate || 'Not supplied'}</dd></div></dl><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Linked rules</p><div className="mt-2 flex flex-wrap gap-2">{(selectedAuthority.linkedRules.length ? selectedAuthority.linkedRules : ['No linked rules supplied']).map((ruleId) => <Badge key={ruleId} variant="slate" size="sm">{ruleId}</Badge>)}</div></div><div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3"><p className="text-xs font-semibold uppercase tracking-wider text-amber-300">Source limitations</p><ul className="mt-2 space-y-1 text-sm text-amber-100">{(selectedAuthority.limitations.length ? selectedAuthority.limitations : ['No source limitation text supplied.']).map((item) => <li key={item}>- {item}</li>)}</ul></div>{selectedAuthority.sourceUrl && <a href={selectedAuthority.sourceUrl} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 px-3 py-2 text-sm font-semibold text-gold hover:bg-gold/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60">Open source record <ExternalLink className="h-4 w-4" aria-hidden="true" /></a>}</div> : <EmptyState title="No authority selected" detail="Select a linked authority from a rule or choose an authority from the viewer list." />}
          </Card>

          <Card padding="lg" className="rounded-lg">
            <div className="flex items-start justify-between gap-3"><div><h2 className="flex items-center gap-2 text-xl font-bold text-white"><Gavel className="h-5 w-5 text-gold" aria-hidden="true" /> Review Queue</h2><p className="mt-2 text-sm text-slate-400">Authorized users can inspect pending legal review, conflicts, stale authorities, and challenges.</p></div><Badge variant={authorizedQueueVisible ? 'green' : 'amber'}>{authorizedQueueVisible ? 'Authorized view' : 'Restricted'}</Badge></div>
            <button type="button" className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-4 py-2 text-sm font-semibold text-gold transition hover:bg-gold/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60" onClick={() => setAuthorizedQueueVisible((visible) => !visible)}>{authorizedQueueVisible ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <LockKeyhole className="h-4 w-4" aria-hidden="true" />}{authorizedQueueVisible ? 'Hide authorized queue' : 'Show authorized queue'}</button>
            {!authorizedQueueVisible ? <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400"><p className="flex items-center gap-2 font-semibold text-slate-200"><LockKeyhole className="h-4 w-4 text-amber-400" aria-hidden="true" /> Authorization required</p><p className="mt-2">The queue is hidden by default because production review requires professional authorization. This frontend does not approve rules.</p></div> : data.reviewQueue.length === 0 ? <EmptyState title="Review queue is empty" detail="No pending rules, conflicts, stale authorities, or challenges were returned by the API." /> : <div className="mt-4 space-y-3">{data.reviewQueue.map((item) => <article key={item.id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3"><div className="flex flex-wrap items-center gap-2"><Badge variant="blue" size="sm">{queueTypeLabels[item.type]}</Badge><Badge variant={statusVariant(item.status)} size="sm">{formatStatus(item.status)}</Badge></div><h3 className="mt-3 text-sm font-bold text-white">{item.label}</h3><p className="mt-2 text-sm text-slate-400">{item.reason}</p><dl className="mt-3 grid gap-2 text-xs text-slate-400"><div className="flex items-center justify-between gap-3"><dt className="uppercase tracking-wider text-slate-500">Owner</dt><dd className="text-right text-slate-200">{item.owner}</dd></div><div className="flex items-center justify-between gap-3"><dt className="uppercase tracking-wider text-slate-500">Due</dt><dd className="text-right text-slate-200">{item.due}</dd></div><div className="flex items-center justify-between gap-3"><dt className="uppercase tracking-wider text-slate-500">Required role</dt><dd className="text-right text-slate-200">{formatStatus(item.authorizationRequired)}</dd></div></dl></article>)}</div>}
          </Card>

          <Card padding="md" className="rounded-lg border-amber-500/30"><p className="flex items-center gap-2 text-sm font-semibold text-amber-200"><BadgeCheck className="h-4 w-4" aria-hidden="true" /> Production gate posture</p><p className="mt-2 text-sm leading-6 text-slate-400">New Jersey remains a non-production pilot here. The UI intentionally exposes review warnings, source limits, and zero production-eligible rules.</p><div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><CalendarClock className="h-3.5 w-3.5" aria-hidden="true" /> Effective-date and stale-source status must be checked before any professional use.</div></Card>
        </aside>
      </div>
    </section>
  );
}
