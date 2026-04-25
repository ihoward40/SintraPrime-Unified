import { clsx } from 'clsx';

type BadgeVariant = 'gold' | 'green' | 'red' | 'blue' | 'amber' | 'slate' | 'purple';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  gold: 'bg-gold/15 text-gold border-gold/30',
  green: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  red: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
  blue: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  amber: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  slate: 'bg-slate-700/50 text-slate-400 border-slate-600/30',
  purple: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
};

const dotColors: Record<BadgeVariant, string> = {
  gold: 'bg-gold',
  green: 'bg-emerald-400',
  red: 'bg-rose-400',
  blue: 'bg-blue-400',
  amber: 'bg-amber-400',
  slate: 'bg-slate-400',
  purple: 'bg-purple-400',
};

export default function Badge({ children, variant = 'slate', size = 'md', dot, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-xs',
        variants[variant],
        className
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
}
