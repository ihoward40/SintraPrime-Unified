import { motion } from 'framer-motion';
import { Scale, Calendar, ChevronRight, AlertCircle } from 'lucide-react';
import Badge from '../ui/Badge';
import type { Case } from '../../types/legal';
import { clsx } from 'clsx';

const statusColors: Record<string, string> = {
  intake: 'blue',
  research: 'amber',
  drafting: 'purple',
  filing: 'gold',
  monitoring: 'green',
  closed: 'slate',
};

interface CaseCardProps {
  case_: Case;
  onClick?: () => void;
  compact?: boolean;
}

export default function CaseCard({ case_, onClick, compact }: CaseCardProps) {
  const urgencyDays = case_.nextDeadline
    ? Math.ceil((new Date(case_.nextDeadline).getTime() - Date.now()) / 86400000)
    : null;

  return (
    <motion.div
      whileHover={{ y: -1 }}
      onClick={onClick}
      className={clsx(
        'bg-slate-900/60 border rounded-xl cursor-pointer transition-all group',
        urgencyDays !== null && urgencyDays <= 7
          ? 'border-amber-500/40 hover:border-amber-500/60'
          : 'border-slate-700/40 hover:border-gold/30',
        compact ? 'p-3' : 'p-4'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gold/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Scale className="w-4 h-4 text-gold" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-mono text-slate-500">{case_.caseNumber}</span>
              <Badge variant={statusColors[case_.status] as any} size="sm" className="capitalize">{case_.status}</Badge>
              {urgencyDays !== null && urgencyDays <= 7 && (
                <div className="flex items-center gap-1 text-amber-400 text-[10px]">
                  <AlertCircle className="w-3 h-3" />
                  <span>{urgencyDays}d deadline</span>
                </div>
              )}
            </div>
            <h4 className={clsx('font-semibold text-slate-200 mt-0.5 leading-tight', compact ? 'text-sm' : 'text-sm')}>
              {case_.title}
            </h4>
            {!compact && (
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{case_.description}</p>
            )}
            <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-500 flex-wrap">
              <span className="capitalize">{case_.practiceArea.replace('_', ' ')}</span>
              {case_.court && <><span>·</span><span>{case_.court}</span></>}
              {case_.estimatedValue && (
                <><span>·</span><span className="text-emerald-400">${(case_.estimatedValue / 1000).toFixed(0)}K est.</span></>
              )}
            </div>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors flex-shrink-0 mt-1" />
      </div>

      {case_.nextDeadline && !compact && (
        <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center gap-1.5 text-xs text-slate-500">
          <Calendar className="w-3.5 h-3.5" />
          <span>Next deadline: {new Date(case_.nextDeadline).toLocaleDateString()}</span>
        </div>
      )}
    </motion.div>
  );
}
