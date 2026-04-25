import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scale,
  Search,
  Filter,
  ChevronRight,
  FileText,
  Gavel,
  AlertCircle,
  CheckCircle,
  Clock,
  BookOpen,
  Shield,
  Building2,
  Landmark,
  Globe,
  Users,
  TrendingUp,
  Lock,
  Briefcase,
  Home,
  Heart,
  Leaf,
  DollarSign,
  Ship,
  Cpu,
  Star,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { useLegalStore } from '../store/legalStore';
import { clsx } from 'clsx';
import type { CaseStatus } from '../types/legal';

const practiceAreas = [
  { id: 'civil_rights', name: 'Civil Rights', icon: Scale, color: 'text-gold', bg: 'bg-gold/10', cases: 3, description: 'Constitutional violations, discrimination, § 1983 claims, Fair Housing Act' },
  { id: 'criminal_defense', name: 'Criminal Defense', icon: Shield, color: 'text-rose-400', bg: 'bg-rose-500/10', cases: 1, description: 'Felonies, misdemeanors, federal crimes, appeals, habeas corpus' },
  { id: 'constitutional', name: 'Constitutional', icon: Landmark, color: 'text-blue-400', bg: 'bg-blue-500/10', cases: 2, description: 'First Amendment, Due Process, Equal Protection, Bill of Rights' },
  { id: 'contract', name: 'Contract Law', icon: FileText, color: 'text-emerald-400', bg: 'bg-emerald-500/10', cases: 4, description: 'Formation, breach, remedies, UCC Article 2, commercial agreements' },
  { id: 'tort', name: 'Tort Law', icon: AlertCircle, color: 'text-amber-400', bg: 'bg-amber-500/10', cases: 2, description: 'Negligence, strict liability, intentional torts, products liability' },
  { id: 'property', name: 'Property Law', icon: Home, color: 'text-purple-400', bg: 'bg-purple-500/10', cases: 3, description: 'Real property, landlord-tenant, adverse possession, easements' },
  { id: 'family', name: 'Family Law', icon: Heart, color: 'text-pink-400', bg: 'bg-pink-500/10', cases: 0, description: 'Divorce, custody, adoption, domestic violence, guardianship' },
  { id: 'estate', name: 'Estate Planning', icon: BookOpen, color: 'text-cyan-400', bg: 'bg-cyan-500/10', cases: 2, description: 'Wills, probate, power of attorney, healthcare directives' },
  { id: 'trust', name: 'Trust Law', icon: Lock, color: 'text-gold', bg: 'bg-gold/10', cases: 3, description: 'Express trusts, UCC filings, asset protection, 30 trust doctrines' },
  { id: 'tax', name: 'Tax Law', icon: DollarSign, color: 'text-green-400', bg: 'bg-green-500/10', cases: 1, description: 'Federal income tax, estate tax, corporate tax, IRS disputes' },
  { id: 'corporate', name: 'Corporate Law', icon: Building2, color: 'text-blue-300', bg: 'bg-blue-400/10', cases: 5, description: 'Entity formation, governance, M&A, shareholder disputes, fiduciary duty' },
  { id: 'securities', name: 'Securities Law', icon: TrendingUp, color: 'text-emerald-300', bg: 'bg-emerald-400/10', cases: 0, description: 'SEC compliance, IPO, insider trading, investment advisers' },
  { id: 'bankruptcy', name: 'Bankruptcy', icon: Briefcase, color: 'text-orange-400', bg: 'bg-orange-500/10', cases: 1, description: 'Chapter 7, 11, 13 bankruptcy, automatic stay, asset liquidation' },
  { id: 'immigration', name: 'Immigration', icon: Globe, color: 'text-teal-400', bg: 'bg-teal-500/10', cases: 0, description: 'Visas, deportation defense, asylum, naturalization, DACA' },
  { id: 'ip', name: 'Intellectual Property', icon: Cpu, color: 'text-violet-400', bg: 'bg-violet-500/10', cases: 1, description: 'Patents, trademarks, copyright, trade secrets, licensing' },
  { id: 'employment', name: 'Employment Law', icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10', cases: 2, description: 'Discrimination, wrongful termination, FLSA, FMLA, non-compete' },
  { id: 'environmental', name: 'Environmental', icon: Leaf, color: 'text-lime-400', bg: 'bg-lime-500/10', cases: 0, description: 'Clean Air Act, EPA regulations, toxic torts, CERCLA liability' },
  { id: 'administrative', name: 'Administrative', icon: Gavel, color: 'text-slate-300', bg: 'bg-slate-700/50', cases: 0, description: 'Agency rulemaking, APA compliance, federal/state agency appeals' },
  { id: 'international', name: 'International', icon: Ship, color: 'text-sky-400', bg: 'bg-sky-500/10', cases: 0, description: 'Cross-border transactions, treaties, private international law' },
  { id: 'ucc', name: 'UCC / Commercial', icon: Star, color: 'text-amber-300', bg: 'bg-amber-400/10', cases: 2, description: 'Articles 1-9, secured transactions, negotiable instruments, leases' },
];

const kanbanColumns: { status: CaseStatus; label: string; color: string }[] = [
  { status: 'intake', label: 'Intake', color: 'text-slate-400' },
  { status: 'research', label: 'Research', color: 'text-blue-400' },
  { status: 'drafting', label: 'Drafting', color: 'text-amber-400' },
  { status: 'filing', label: 'Filing', color: 'text-purple-400' },
  { status: 'monitoring', label: 'Monitoring', color: 'text-emerald-400' },
  { status: 'closed', label: 'Closed', color: 'text-slate-500' },
];

const priorityColors = {
  critical: 'red',
  high: 'amber',
  medium: 'blue',
  low: 'slate',
} as const;

export default function LegalHub() {
  const { cases } = useLegalStore();
  const [activeTab, setActiveTab] = useState<'areas' | 'kanban' | 'motion'>('areas');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArea, setSelectedArea] = useState<string | null>(null);
  const [motionType, setMotionType] = useState('');
  const [motionContext, setMotionContext] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedMotion, setGeneratedMotion] = useState('');

  const filteredAreas = practiceAreas.filter((area) =>
    !searchQuery || area.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const casesByStatus = (status: CaseStatus) => cases.filter((c) => c.status === status);

  const handleGenerateMotion = async () => {
    if (!motionType || !motionContext) return;
    setIsGenerating(true);
    await new Promise((r) => setTimeout(r, 2000));
    setGeneratedMotion(`UNITED STATES DISTRICT COURT
SOUTHERN DISTRICT OF NEW YORK

────────────────────────────────────
IN THE MATTER OF:
MARCUS A. SINTRA,
                    Plaintiff,
        vs.
METROPOLITAN HOUSING AUTHORITY,
                    Defendant.
────────────────────────────────────
Case No.: 2024-CV-1847

${motionType.toUpperCase().replace(/_/g, ' ')}

COMES NOW, Plaintiff Marcus A. Sintra, by and through undersigned counsel, and respectfully moves this Court pursuant to Fed. R. Civ. P. 12(b)(6) for the following relief:

I. INTRODUCTION

${motionContext}

Plaintiff respectfully submits that the above-captioned matter warrants judicial intervention based on the following grounds, supported by controlling authority and the applicable facts of record.

II. STATEMENT OF FACTS

On or about January 15, 2024, Plaintiff filed the instant action alleging violations of the Fair Housing Act, 42 U.S.C. § 3604, and 42 U.S.C. § 1983. The discriminatory practices alleged herein have caused substantial harm to Plaintiff and similarly situated individuals.

III. LEGAL STANDARD

This Court has jurisdiction pursuant to 28 U.S.C. § 1331. The standard for [motion type] requires the movant to demonstrate...

IV. ARGUMENT

A. The Applicable Legal Standard Favors Plaintiff

Under controlling Ninth Circuit precedent, including Smith v. City of Oakland, 538 F.3d 1234 (9th Cir. 2008), the Court must consider...

B. Plaintiff Has Demonstrated the Required Elements

1. Likelihood of Success on the Merits...
2. Irreparable Harm...
3. Balance of Equities...
4. Public Interest...

V. CONCLUSION

WHEREFORE, Plaintiff respectfully requests that this Court GRANT this Motion and issue an Order granting the relief herein.

Respectfully submitted,
/s/ Marcus A. Sintra, Esq.
Bar No. CA-123456
SINTRAPRIME LAW GROUP
Dated: ${new Date().toLocaleDateString()}`);
    setIsGenerating(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Legal Hub</h1>
          <p className="text-slate-500 text-sm mt-1">20 practice areas · {cases.length} active matters</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" icon={Filter}>Filter</Button>
          <Button size="sm" icon={Plus as React.ElementType}>New Case</Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900/60 border border-slate-700/40 rounded-xl w-fit">
        {[
          { id: 'areas', label: 'Practice Areas' },
          { id: 'kanban', label: 'Case Board' },
          { id: 'motion', label: 'Motion Drafter' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as 'areas' | 'kanban' | 'motion')}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
              activeTab === tab.id
                ? 'bg-gold/15 text-gold border border-gold/30'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'areas' && (
          <motion.div key="areas" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {/* Search */}
            <div className="relative mb-5">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search practice areas..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-dark pl-10 max-w-sm"
              />
            </div>

            {/* Practice Area Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredAreas.map((area, i) => (
                <motion.div
                  key={area.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => setSelectedArea(selectedArea === area.id ? null : area.id)}
                  className={clsx(
                    'glass-card p-4 cursor-pointer transition-all duration-200 hover:-translate-y-1',
                    selectedArea === area.id && 'border-gold/40 bg-gold/5'
                  )}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center', area.bg)}>
                      <area.icon className={clsx('w-5 h-5', area.color)} />
                    </div>
                    {area.cases > 0 && (
                      <Badge variant="gold" size="sm">{area.cases}</Badge>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-1">{area.name}</h3>
                  <AnimatePresence>
                    {selectedArea === area.id ? (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-xs text-slate-400 leading-relaxed"
                      >
                        {area.description}
                      </motion.p>
                    ) : (
                      <p className="text-xs text-slate-600 truncate">{area.description.split(',')[0]}</p>
                    )}
                  </AnimatePresence>
                  {selectedArea === area.id && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex gap-2 mt-3"
                    >
                      <Button variant="gold" size="sm" fullWidth>Open Cases</Button>
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'kanban' && (
          <motion.div key="kanban" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-3 xl:grid-cols-6 gap-3">
              {kanbanColumns.map((col) => {
                const colCases = casesByStatus(col.status);
                return (
                  <div key={col.status} className="flex flex-col gap-3">
                    <div className="flex items-center justify-between px-2">
                      <span className={clsx('text-xs font-semibold uppercase tracking-wider', col.color)}>
                        {col.label}
                      </span>
                      <span className="text-xs text-slate-600 bg-slate-800/50 px-1.5 py-0.5 rounded-md">
                        {colCases.length}
                      </span>
                    </div>
                    <div className="space-y-2 min-h-24">
                      {colCases.map((c, i) => (
                        <motion.div
                          key={c.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="glass-card p-3 cursor-pointer hover:border-slate-600/60 transition-all group"
                        >
                          <div className="flex items-start gap-1.5 mb-2">
                            <Badge variant={priorityColors[c.priority]} size="sm">{c.priority}</Badge>
                          </div>
                          <p className="text-xs font-medium text-slate-300 group-hover:text-white leading-snug mb-2">
                            {c.title}
                          </p>
                          <p className="text-[10px] text-slate-600">{c.caseNumber}</p>
                          {c.nextDeadline && (
                            <div className="flex items-center gap-1 mt-2">
                              <Clock className="w-3 h-3 text-slate-600" />
                              <span className="text-[10px] text-slate-600">
                                {new Date(c.nextDeadline).toLocaleDateString()}
                              </span>
                            </div>
                          )}
                        </motion.div>
                      ))}
                      {colCases.length === 0 && (
                        <div className="border border-dashed border-slate-800 rounded-xl h-20 flex items-center justify-center">
                          <span className="text-xs text-slate-700">Drop here</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {activeTab === 'motion' && (
          <motion.div key="motion" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {/* Form */}
              <Card padding="lg">
                <CardHeader title="AI Motion Drafter" subtitle="Generate professional legal motions" />
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Motion Type *</label>
                    <select
                      value={motionType}
                      onChange={(e) => setMotionType(e.target.value)}
                      className="input-dark"
                    >
                      <option value="">Select motion type...</option>
                      <option value="motion_to_dismiss">Motion to Dismiss (Rule 12(b)(6))</option>
                      <option value="summary_judgment">Motion for Summary Judgment</option>
                      <option value="preliminary_injunction">Motion for Preliminary Injunction</option>
                      <option value="temporary_restraining_order">Temporary Restraining Order</option>
                      <option value="motion_in_limine">Motion in Limine</option>
                      <option value="habeas_corpus">Writ of Habeas Corpus</option>
                      <option value="mandamus">Writ of Mandamus</option>
                      <option value="compel_discovery">Motion to Compel Discovery</option>
                      <option value="protective_order">Protective Order</option>
                      <option value="sanctions">Motion for Sanctions</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Case</label>
                    <select className="input-dark">
                      <option value="">Select case...</option>
                      {cases.map((c) => (
                        <option key={c.id} value={c.id}>{c.title}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Context & Key Arguments *</label>
                    <textarea
                      rows={5}
                      value={motionContext}
                      onChange={(e) => setMotionContext(e.target.value)}
                      placeholder="Describe the key facts, legal arguments, and relief requested. The AI will generate a professional motion based on your input..."
                      className="input-dark resize-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Jurisdiction</label>
                    <select className="input-dark">
                      <option>S.D.N.Y. (Federal)</option>
                      <option>E.D.N.Y. (Federal)</option>
                      <option>D. Del. (Federal)</option>
                      <option>New York Supreme Court (State)</option>
                      <option>California Superior Court (State)</option>
                    </select>
                  </div>
                  <Button
                    fullWidth
                    onClick={handleGenerateMotion}
                    loading={isGenerating}
                    disabled={!motionType || !motionContext}
                    icon={FileText}
                  >
                    {isGenerating ? 'Generating Motion...' : 'Generate Motion'}
                  </Button>
                </div>
              </Card>

              {/* Preview */}
              <Card padding="lg">
                <CardHeader
                  title="Motion Preview"
                  subtitle={generatedMotion ? 'AI-generated draft' : 'Preview appears here'}
                  action={generatedMotion && (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">Copy</Button>
                      <Button size="sm">Download</Button>
                    </div>
                  )}
                />
                {generatedMotion ? (
                  <div className="h-96 overflow-y-auto">
                    <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                      {generatedMotion}
                    </pre>
                  </div>
                ) : (
                  <div className="h-96 flex items-center justify-center border border-dashed border-slate-700/50 rounded-xl">
                    <div className="text-center text-slate-600">
                      <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">Fill out the form and click Generate</p>
                      <p className="text-xs mt-1">AI will draft a professional legal motion</p>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Plus icon shim
function Plus({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}
