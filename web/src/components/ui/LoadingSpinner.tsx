import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export default function LoadingSpinner({ size = 'md', label }: LoadingSpinnerProps) {
  const sizes = { sm: 24, md: 40, lg: 64 };
  const s = sizes[size];

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={s} height={s} viewBox="0 0 40 40">
        <motion.circle
          cx="20" cy="20" r="16"
          fill="none"
          stroke="rgba(212,175,55,0.2)"
          strokeWidth="3"
        />
        <motion.circle
          cx="20" cy="20" r="16"
          fill="none"
          stroke="#D4AF37"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="80"
          strokeDashoffset="60"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: '20px 20px' }}
        />
      </svg>
      {label && <span className="text-sm text-slate-500">{label}</span>}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <LoadingSpinner size="lg" label="Loading..." />
    </div>
  );
}
