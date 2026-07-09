/**
 * LiveCaseManagement — Real case data from FastAPI recovery endpoint
 * Second vertical slice: Dashboard → Select Case → View Details
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Scale, FileText, AlertCircle, ChevronRight, Search,
  Shield, Clock, ArrowLeft,
} from 'lucide-react';
import recoveryApi, { RecoveryCase, DashboardStats } from '../api/recovery';

interface EvidenceItem {
  evidence_id: string;
  title: string;
  evidence_type: string;
}

interface Receipt {
  receipt_id: string;
  action: string;
}

interface CasePacket {
  evidence?: EvidenceItem[];
  receipts?: Receipt[];
}

export default function LiveCaseManagement() {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<RecoveryCase | null>(null);
  const [casePacket, setCasePacket] = useState<CasePacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await recoveryApi.getCases();
        setCases(data.cases);
        setError(null);
      } catch (err) {
        setError('Failed to load cases');
      } finally {
        setLoading(false);
      }
    };
    fetchCases();
  }, []);

  const handleSelectCase = async (c: RecoveryCase) => {
    setSelectedCase(c);
    setCasePacket(null);
    try {
      const packet = await recoveryApi.getCasePacket(c.case_id);
      setCasePacket(packet);
    } catch {
      // Not all cases have packets — that's OK
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gold animate-pulse text-lg">Loading cases...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  // Case Detail View
  if (selectedCase) {
    return (
      <div className="space-y-6">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <button
            onClick={() => setSelectedCase(null)}
            className="flex items-center gap-2 text-slate-400 hover:text-gold transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Cases
          </button>

          <div className="glass-card rounded-xl p-6 border border-slate-700/60">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-xl font-bold text-white">{selectedCase.case_name}</h1>
                <p className="text-xs text-slate-500 font-mono mt-1">{selectedCase.case_id}</p>
              </div>
              <div className="flex gap-2">
                <span className={`text-xs px-2 py-1 rounded ${
                  selectedCase.priority === 'high'
                    ? 'bg-red-500/10 text-red-400'
                    : 'bg-amber-500/10 text-amber-400'
                }`}>
                  {selectedCase.priority.toUpperCase()}
                </span>
                <span className="text-xs px-2 py-1 rounded bg-blue-500/10 text-blue-400">
                  {selectedCase.status}
                </span>
              </div>
            </div>

            {selectedCase.notes && (
              <p className="text-sm text-slate-400 mb-4">{selectedCase.notes}</p>
            )}

            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="flex items-center gap-2 text-sm">
                <Shield className="w-4 h-4 text-red-400" />
                <span className="text-slate-400">External Action:</span>
                <span className="text-red-400 font-medium">{selectedCase.external_action}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-slate-400" />
                <span className="text-slate-400">Created:</span>
                <span className="text-slate-300">{new Date(selectedCase.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Case Packet */}
          {casePacket && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-xl p-6 border border-slate-700/60 mt-4"
            >
              <h2 className="text-lg font-semibold text-white mb-4">Case Packet</h2>
              {casePacket.evidence && casePacket.evidence.length > 0 ? (
                <div className="space-y-2">
                  {casePacket.evidence.map((ev) => (
                    <div key={ev.evidence_id} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                      <div>
                        <div className="text-sm text-white">{ev.title}</div>
                        <div className="text-xs text-slate-500 font-mono">{ev.evidence_id}</div>
                      </div>
                      <span className="text-xs text-slate-400">{ev.evidence_type}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No evidence items in case packet.</p>
              )}

              {casePacket.receipts && casePacket.receipts.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-semibold text-slate-300 mb-2">Receipts</h3>
                  <div className="space-y-1">
                    {casePacket.receipts.map((r) => (
                      <div key={r.receipt_id} className="text-xs text-slate-400 p-2 rounded bg-slate-800/30">
                        <span className="font-mono">{r.receipt_id}</span>: {r.action}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Controls */}
          <div className="glass-card rounded-xl p-6 border border-slate-700/60 mt-4">
            <h2 className="text-lg font-semibold text-white mb-4">Controls</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <div>
                  <div className="text-sm text-white">Approval Required</div>
                  <div className="text-xs text-slate-500">All external actions are locked pending explicit approval</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/30">
                <FileText className="w-5 h-5 text-blue-400" />
                <div>
                  <div className="text-sm text-white">Evidence Intake Mode</div>
                  <div className="text-xs text-slate-500">System is collecting evidence. No external communications permitted.</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  // Case List View
  const filteredCases = cases.filter(c =>
    c.case_name.toLowerCase().includes(search.toLowerCase()) ||
    c.case_id.toLowerCase().includes(search.toLowerCase())
  );

  const highPriority = filteredCases.filter(c => c.priority === 'high');
  const mediumPriority = filteredCases.filter(c => c.priority === 'medium');

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-white">Case Management</h1>
        <p className="text-slate-400 text-sm">{cases.length} active cases | External action: LOCKED</p>
      </motion.div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search cases..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/50 border border-slate-700/60 text-white placeholder-slate-500 focus:outline-none focus:border-gold/50"
        />
      </div>

      {/* High Priority */}
      {highPriority.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            High Priority ({highPriority.length})
          </h2>
          <div className="space-y-2">
            {highPriority.map((c) => (
              <motion.button
                key={c.case_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                onClick={() => handleSelectCase(c)}
                className="w-full text-left p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 hover:border-gold/40 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Scale className="w-5 h-5 text-gold" />
                    <div>
                      <div className="text-white font-medium">{c.case_name}</div>
                      <div className="text-xs text-slate-500 font-mono">{c.case_id}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-amber-400 px-2 py-1 rounded bg-amber-500/10">{c.status}</span>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-gold transition-colors" />
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Medium Priority */}
      {mediumPriority.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 mb-3">Medium Priority ({mediumPriority.length})</h2>
          <div className="space-y-2">
            {mediumPriority.map((c) => (
              <motion.button
                key={c.case_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                onClick={() => handleSelectCase(c)}
                className="w-full text-left p-4 rounded-xl bg-slate-800/30 border border-slate-700/40 hover:border-slate-600 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Scale className="w-5 h-5 text-slate-500" />
                    <div>
                      <div className="text-slate-300 font-medium">{c.case_name}</div>
                      <div className="text-xs text-slate-600 font-mono">{c.case_id}</div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-700 group-hover:text-slate-400 transition-colors" />
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}