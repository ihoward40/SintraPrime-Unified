import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Sparkles, Download, Copy, RefreshCw, ChevronRight, Check } from 'lucide-react';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { clsx } from 'clsx';

const motionTypes = [
  'Motion to Dismiss (12(b)(6))',
  'Motion for Summary Judgment',
  'Motion for Preliminary Injunction',
  'Motion in Limine',
  'Motion to Compel Discovery',
  'Motion to Suppress Evidence',
  'Motion for Change of Venue',
  'Motion for Default Judgment',
  'Notice of Appeal',
  'Opposition to Motion to Dismiss',
];

const mockGeneratedMotion = `UNITED STATES DISTRICT COURT
FOR THE SOUTHERN DISTRICT OF NEW YORK

─────────────────────────────────────
PLAINTIFF,
                     Plaintiff,
v.                                              Case No. 1:2024-cv-01847

DEFENDANT,
                     Defendant.
─────────────────────────────────────

MEMORANDUM OF LAW IN SUPPORT OF
PLAINTIFF'S MOTION FOR PRELIMINARY INJUNCTION

INTRODUCTION

Plaintiff respectfully submits this memorandum of law in support of their motion for a preliminary injunction pursuant to Federal Rule of Civil Procedure 65. Plaintiff has demonstrated a substantial likelihood of success on the merits, will suffer irreparable harm absent injunctive relief, that the balance of equities tips decidedly in Plaintiff's favor, and that the public interest is served by granting the requested relief.

STATEMENT OF FACTS

...

ARGUMENT

I. PLAINTIFF SATISFIES ALL FOUR REQUIREMENTS FOR A PRELIMINARY INJUNCTION

A. Likelihood of Success on the Merits

Plaintiff demonstrates a clear likelihood of success on the merits of their claims under the Fair Housing Act, 42 U.S.C. § 3604. Pursuant to Texas Department of Housing and Community Affairs v. Inclusive Communities Project, Inc., 576 U.S. 519 (2015), disparate-impact claims are cognizable under the FHA...

[Motion continues for 18 pages...]`;

export default function MotionDrafter() {
  const [step, setStep] = useState<'form' | 'generating' | 'preview'>('form');
  const [motionType, setMotionType] = useState('');
  const [caseNumber, setCaseNumber] = useState('');
  const [facts, setFacts] = useState('');
  const [copied, setCopied] = useState(false);

  const handleGenerate = () => {
    setStep('generating');
    setTimeout(() => setStep('preview'), 2500);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(mockGeneratedMotion).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div>
      <AnimatePresence mode="wait">
        {step === 'form' && (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            <div>
              <label className="text-xs text-slate-500 font-medium uppercase block mb-1.5">Motion Type</label>
              <select
                value={motionType}
                onChange={(e) => setMotionType(e.target.value)}
                className="input-dark text-sm"
              >
                <option value="">Select motion type...</option>
                {motionTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-500 font-medium uppercase block mb-1.5">Case Number</label>
              <input
                type="text"
                value={caseNumber}
                onChange={(e) => setCaseNumber(e.target.value)}
                placeholder="e.g. 1:2024-cv-01847"
                className="input-dark text-sm"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 font-medium uppercase block mb-1.5">Relevant Facts & Arguments</label>
              <textarea
                value={facts}
                onChange={(e) => setFacts(e.target.value)}
                rows={4}
                placeholder="Describe the key facts, legal arguments, and relief sought..."
                className="input-dark text-sm resize-none"
              />
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs text-slate-500 font-medium uppercase block mb-1.5">Court</label>
                <input type="text" placeholder="e.g. S.D.N.Y." className="input-dark text-sm" />
              </div>
              <div className="flex-1">
                <label className="text-xs text-slate-500 font-medium uppercase block mb-1.5">Judge</label>
                <input type="text" placeholder="e.g. Hon. J. Williams" className="input-dark text-sm" />
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={!motionType}
              icon={Sparkles}
              fullWidth
            >
              Generate Motion with AI
            </Button>
          </motion.div>
        )}

        {step === 'generating' && (
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-12 gap-4"
          >
            <div className="w-14 h-14 rounded-2xl bg-gold/10 border border-gold/20 flex items-center justify-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              >
                <Sparkles className="w-7 h-7 text-gold" />
              </motion.div>
            </div>
            <div className="text-center">
              <p className="font-semibold text-slate-200">Drafting Your Motion</p>
              <p className="text-xs text-slate-500 mt-1">Analyzing precedents, constructing arguments...</p>
            </div>
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 rounded-full bg-gold"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          </motion.div>
        )}

        {step === 'preview' && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="green" dot>Generated</Badge>
                <span className="text-xs text-slate-500">{motionType}</span>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" icon={copied ? Check : Copy} onClick={handleCopy}>
                  {copied ? 'Copied' : 'Copy'}
                </Button>
                <Button size="sm" icon={Download}>Download</Button>
                <Button size="sm" variant="ghost" icon={RefreshCw} onClick={() => setStep('form')}>
                  Revise
                </Button>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800/60 rounded-xl p-4 max-h-80 overflow-y-auto">
              <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                {mockGeneratedMotion}
              </pre>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: 'Pages', value: '18' },
                { label: 'Citations', value: '24' },
                { label: 'Arguments', value: '6' },
              ].map((stat) => (
                <div key={stat.label} className="p-2 bg-slate-800/40 rounded-lg">
                  <div className="text-base font-bold text-gold">{stat.value}</div>
                  <div className="text-[10px] text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
