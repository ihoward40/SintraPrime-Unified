import { motion } from 'framer-motion';
import { clsx } from 'clsx';

interface CreditScoreGaugeProps {
  score: number;
  previousScore?: number;
  size?: 'sm' | 'md' | 'lg';
}

function getScoreLabel(score: number): { label: string; color: string } {
  if (score >= 800) return { label: 'Exceptional', color: '#10B981' };
  if (score >= 740) return { label: 'Very Good', color: '#34D399' };
  if (score >= 670) return { label: 'Good', color: '#D4AF37' };
  if (score >= 580) return { label: 'Fair', color: '#F59E0B' };
  return { label: 'Poor', color: '#F43F5E' };
}

export default function CreditScoreGauge({ score, previousScore, size = 'md' }: CreditScoreGaugeProps) {
  const { label, color } = getScoreLabel(score);
  const pct = (score - 300) / (850 - 300);
  const radius = size === 'lg' ? 80 : size === 'md' ? 60 : 40;
  const strokeWidth = size === 'lg' ? 12 : 8;
  const svgSize = (radius + strokeWidth) * 2;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75;
  const dashOffset = arcLength * (1 - pct);

  const centerX = svgSize / 2;
  const centerY = svgSize / 2;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: svgSize, height: svgSize * 0.75 + 10 }}>
        <svg
          width={svgSize}
          height={svgSize}
          style={{ marginTop: -(svgSize * 0.25) }}
          className="overflow-visible"
        >
          {/* Background arc */}
          <circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke="#1E293B"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform={`rotate(135 ${centerX} ${centerY})`}
          />
          {/* Score arc */}
          <motion.circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            transform={`rotate(135 ${centerX} ${centerY})`}
            initial={{ strokeDashoffset: arcLength }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
            style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
          />
        </svg>
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className={clsx('font-bold leading-none', size === 'lg' ? 'text-5xl' : size === 'md' ? 'text-3xl' : 'text-2xl')}
            style={{ color }}
          >
            {score}
          </motion.div>
          <div className={clsx('font-semibold mt-1', size === 'lg' ? 'text-base' : 'text-sm')} style={{ color }}>
            {label}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between w-full text-[10px] text-slate-600 mt-2 px-2">
        <span>300</span>
        <span>580</span>
        <span>670</span>
        <span>740</span>
        <span>800</span>
        <span>850</span>
      </div>

      {previousScore && (
        <div className="mt-2 text-xs text-slate-500">
          {score > previousScore ? (
            <span className="text-emerald-400">+{score - previousScore} vs last month</span>
          ) : (
            <span className="text-rose-400">{score - previousScore} vs last month</span>
          )}
        </div>
      )}
    </div>
  );
}
