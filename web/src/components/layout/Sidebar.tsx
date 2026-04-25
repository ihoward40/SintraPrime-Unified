import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Scale,
  TrendingUp,
  BookOpen,
  FolderOpen,
  FileText,
  Building2,
  Brain,
  Search,
  Settings,
  ChevronLeft,
  ChevronRight,
  Gavel,
  Shield,
  Star,
} from 'lucide-react';
import { useAppStore } from '../../store/appStore';
import { clsx } from 'clsx';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/legal', label: 'Legal Hub', icon: Scale, badge: '5', badgeColor: 'gold' },
  { path: '/financial', label: 'Financial Empire', icon: TrendingUp },
  { path: '/trust-law', label: 'Trust Law', icon: BookOpen },
  { path: '/cases', label: 'Case Management', icon: Gavel, badge: '3', badgeColor: 'red' },
  { path: '/documents', label: 'Document Vault', icon: FileText },
  { path: '/entities', label: 'Entity Governance', icon: Building2 },
  { path: '/ai-parliament', label: 'AI Parliament', icon: Brain, badge: 'LIVE', badgeColor: 'green' },
  { path: '/caselaw', label: 'Case Law Search', icon: Search },
  { path: '/settings', label: 'Settings', icon: Settings },
];

const badgeStyles: Record<string, string> = {
  gold: 'bg-gold/20 text-gold border border-gold/40',
  red: 'bg-rose-500/20 text-rose-400 border border-rose-500/40',
  green: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40',
  blue: 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
};

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const location = useLocation();

  return (
    <motion.div
      className="fixed left-0 top-0 h-full z-50 flex flex-col"
      animate={{ width: sidebarCollapsed ? 72 : 260 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      style={{
        background: 'linear-gradient(180deg, #0a0f1e 0%, #0F172A 50%, #091223 100%)',
        borderRight: '1px solid rgba(212,175,55,0.15)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800/50">
        <div
          className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #D4AF37, #F5D87A)' }}
        >
          <Scale className="w-5 h-5 text-slate-900" />
        </div>
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="text-sm font-bold text-gold-gradient leading-tight whitespace-nowrap">
                SintraPrime
              </div>
              <div className="text-[10px] text-slate-500 whitespace-nowrap">AI Law & Finance</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path ||
            (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          const Icon = item.icon;

          return (
            <NavLink key={item.path} to={item.path}>
              <motion.div
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 cursor-pointer relative group',
                  isActive
                    ? 'bg-gold/10 text-gold'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                )}
                whileHover={{ x: sidebarCollapsed ? 0 : 2 }}
                whileTap={{ scale: 0.98 }}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-gold rounded-r-full"
                  />
                )}
                <div className={clsx(
                  'flex-shrink-0 w-5 h-5',
                  isActive ? 'text-gold' : ''
                )}>
                  <Icon className="w-5 h-5" />
                </div>

                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex-1 flex items-center justify-between overflow-hidden"
                    >
                      <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
                      {item.badge && (
                        <span className={clsx(
                          'text-[10px] font-semibold px-1.5 py-0.5 rounded-full',
                          badgeStyles[item.badgeColor || 'gold']
                        )}>
                          {item.badge}
                        </span>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Tooltip for collapsed state */}
                {sidebarCollapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-slate-200 text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-slate-700">
                    {item.label}
                    {item.badge && (
                      <span className={clsx('ml-1.5 text-[10px] font-semibold px-1 py-0.5 rounded-full', badgeStyles[item.badgeColor || 'gold'])}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            </NavLink>
          );
        })}
      </nav>

      {/* Status badges */}
      <AnimatePresence>
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-4 py-3 border-t border-slate-800/50"
          >
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[11px] text-emerald-400 font-medium">All Systems Secure</span>
            </div>
            <div className="flex items-center gap-2">
              <Star className="w-3.5 h-3.5 text-gold" />
              <span className="text-[11px] text-slate-500">AI Parliament: Active</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebar}
        className="flex items-center justify-center h-10 border-t border-slate-800/50 text-slate-500 hover:text-gold transition-colors"
      >
        {sidebarCollapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>
    </motion.div>
  );
}
