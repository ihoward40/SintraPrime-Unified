import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { clsx } from 'clsx';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changeLabel?: string;
  icon: React.ElementType;
  iconColor?: string;
  iconBg?: string;
  trend?: 'up' | 'down' | 'neutral';
  index?: number;
  onClick?: () => void;
  highlight?: boolean;
}

export default function StatCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon: Icon,
  iconColor = 'text-gold',
  iconBg = 'bg-gold/10',
  trend,
  index = 0,
  onClick,
  highlight = false,
}: StatCardProps) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-rose-400' : 'text-slate-500';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: 'easeOut' }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      onClick={onClick}
      className={clsx(
        'glass-card p-5 transition-all duration-300',
        onClick && 'cursor-pointer',
        highlight && 'glass-card-gold'
      )}
      style={highlight ? {
        boxShadow: '0 0 30px rgba(212,175,55,0.12)',
      } : undefined}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={clsx('p-2.5 rounded-xl', iconBg)}>
          <Icon className={clsx('w-5 h-5', iconColor)} />
        </div>
        {(change !== undefined || trend) && (
          <div className={clsx('flex items-center gap-1 text-xs font-medium', trendColor)}>
            <TrendIcon className="w-3.5 h-3.5" />
            {change !== undefined && (
              <span>{change > 0 ? '+' : ''}{typeof change === 'number' && !Number.isInteger(change) ? change.toFixed(1) : change}%</span>
            )}
          </div>
        )}
      </div>

      <div>
        <div className="text-2xl font-bold text-slate-100 mb-0.5">{value}</div>
        <div className="text-sm font-medium text-slate-400">{title}</div>
        {subtitle && <div className="text-xs text-slate-600 mt-1">{subtitle}</div>}
        {changeLabel && <div className={clsx('text-xs mt-1', trendColor)}>{changeLabel}</div>}
      </div>
    </motion.div>
  );
}
