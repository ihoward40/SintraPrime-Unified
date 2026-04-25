import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import LoadingSpinner from './LoadingSpinner';

type ButtonVariant = 'gold' | 'outline' | 'ghost' | 'danger' | 'success';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ElementType;
  iconRight?: boolean;
  children?: React.ReactNode;
  fullWidth?: boolean;
}

const variants: Record<ButtonVariant, string> = {
  gold: 'text-slate-900 font-semibold shadow-md hover:shadow-gold active:scale-95',
  outline: 'text-gold border border-gold/40 hover:bg-gold/10 hover:border-gold/70 active:scale-95',
  ghost: 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 active:scale-95',
  danger: 'bg-rose-500/20 text-rose-400 border border-rose-500/30 hover:bg-rose-500/30 active:scale-95',
  success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 active:scale-95',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-lg',
  md: 'px-5 py-2.5 text-sm rounded-xl',
  lg: 'px-7 py-3 text-base rounded-xl',
};

const goldGradient = {
  background: 'linear-gradient(135deg, #D4AF37, #F5D87A)',
};

export default function Button({
  variant = 'gold',
  size = 'md',
  loading = false,
  icon: Icon,
  iconRight = false,
  children,
  fullWidth = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: disabled || loading ? 1 : 0.97 }}
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-200',
        sizes[size],
        variants[variant],
        fullWidth && 'w-full',
        (disabled || loading) && 'opacity-50 cursor-not-allowed',
        className
      )}
      style={variant === 'gold' ? goldGradient : undefined}
      disabled={disabled || loading}
      {...(props as React.ComponentProps<typeof motion.button>)}
    >
      {loading ? (
        <LoadingSpinner size="sm" />
      ) : (
        <>
          {Icon && !iconRight && <Icon className={clsx(size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4')} />}
          {children}
          {Icon && iconRight && <Icon className={clsx(size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4')} />}
        </>
      )}
    </motion.button>
  );
}
