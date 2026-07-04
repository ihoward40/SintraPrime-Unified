/**
 * LiveDashboard — Real data from FastAPI recovery endpoint
 * Replaces placeholder data with live case counts and readiness scores
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Scale, FileText, Shield, AlertCircle, CheckCircle2,
  TrendingUp, Brain, Zap, Activity,
} from 'lucide-react';
import recoveryApi, { DashboardStats } from '../api/recovery';
import systemApi, { SystemHealth } from '../api/system';

export default function LiveDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashData, healthData] = await Promise.all([
          recoveryApi.getDashboard(),
          systemApi.getHealth(),
        ]);
        setStats(dashData);
        setHealth(healthData);
        setError(null);
      } catch (err) {
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gold animate-pulse text-lg">Loading SintraPrime Dashboard...</div>
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

  if (!stats) return null;

  const statCards = [
    {
      title: 'Active Cases',
      value: stats.cases.total,
      icon: Scale,
      color: 'text-gold',
      bg: 'bg-gold/10',
      subtitle: `${stats.cases.high_priority} high priority`,
    },
    {
      title: 'Evidence Items',
      value: stats.evidence.total_items,
      icon: FileText,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      subtitle: `${stats.evidence.total_receipts} receipts logged`,
    },
    {
      title: 'Evidence Intake',
      value: stats.cases.evidence_intake,
      icon: AlertCircle,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      subtitle: 'Awaiting evidence collection',
    },
    {
      title: 'External Action',
      value: stats.external_action.toUpperCase(),
      icon: Shield,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      subtitle: 'All actions approval-gated',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-white">{stats.tenant}</h1>
          <p className="text-slate-400 text-sm">
            {stats.platform_version} | {stats.evidence_kernel}
          </p>
        </div>
        <div className="flex items-center gap-2 text-emerald-400">
          <Activity className="w-4 h-4" />
          <span className="text-sm">Live</span>
        </div>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-card rounded-xl p-5 border border-slate-700/60"
          >
            <div className="flex items-center justify-between mb-3">
              <div className={`p-2 rounded-lg ${card.bg}`}>
                <card.icon className={`w-5 h-5 ${card.color}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">{card.value}</div>
            <div className="text-sm text-slate-400 mt-1">{card.title}</div>
            <div className="text-xs text-slate-500 mt-1">{card.subtitle}</div>
          </motion.div>
        ))}
      </div>

      {/* Case Readiness Scores */}
      {stats.case_readiness.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card rounded-xl p-6 border border-slate-700/60"
        >
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-gold" />
            Case Readiness Scores
          </h2>
          <div className="space-y-4">
            {stats.case_readiness.map((cr) => (
              <div key={cr.case_id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-300 font-mono">{cr.case_id}</span>
                  <span className={`text-sm font-bold ${
                    cr.grade === 'A' || cr.grade === 'B' ? 'text-emerald-400' :
                    cr.grade === 'C' || cr.grade === 'D' ? 'text-amber-400' :
                    'text-red-400'
                  }`}>
                    {cr.overall}% (Grade {cr.grade})
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: 'Repository', value: cr.repository, color: 'bg-blue-500' },
                    { label: 'Evidence', value: cr.evidence, color: 'bg-emerald-500' },
                    { label: 'Legal', value: cr.legal, color: 'bg-purple-500' },
                    { label: 'Procedural', value: cr.procedural, color: 'bg-amber-500' },
                  ].map((dim) => (
                    <div key={dim.label}>
                      <div className="text-xs text-slate-500 mb-1">{dim.label}</div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${dim.color} rounded-full transition-all duration-500`}
                          style={{ width: `${dim.value}%` }}
                        />
                      </div>
                      <div className="text-xs text-slate-400 mt-1">{dim.value}%</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* High Priority Cases */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass-card rounded-xl p-6 border border-slate-700/60"
      >
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          High Priority Cases
        </h2>
        <div className="space-y-2">
          {stats.high_priority_cases.map((c) => (
            <div
              key={c.case_id}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/40"
            >
              <div>
                <div className="text-sm text-white font-medium">{c.name}</div>
                <div className="text-xs text-slate-500 font-mono">{c.case_id}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-amber-400 px-2 py-1 rounded bg-amber-500/10">
                  {c.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* System Health */}
      {health && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card rounded-xl p-6 border border-slate-700/60"
        >
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className={`w-5 h-5 ${health.overall === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}`} />
            System Health
            <span className={`text-xs px-2 py-0.5 rounded ml-2 ${
              health.overall === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
            }`}>
              {health.overall.toUpperCase()}
            </span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(health.subsystems).map(([name, info]) => (
              <div key={name} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/30">
                <div className={`w-2 h-2 rounded-full ${
                  info.status === 'healthy' ? 'bg-emerald-400' :
                  info.status === 'degraded' ? 'bg-amber-400' : 'bg-slate-600'
                }`} />
                <div>
                  <div className="text-xs text-slate-300 capitalize">{name.replace('_', ' ')}</div>
                  <div className="text-xs text-slate-500">{info.status}</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-slate-600 pt-4">
        Last updated: {new Date(stats.timestamp).toLocaleString()}
      </div>
    </div>
  );
}