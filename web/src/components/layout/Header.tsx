import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Search,
  ChevronDown,
  LogOut,
  User,
  Settings,
  CheckCircle,
  AlertTriangle,
  Info,
  DollarSign,
  Scale,
  X,
} from 'lucide-react';
import { useAppStore } from '../../store/appStore';
import { clsx } from 'clsx';
import { formatDistanceToNow } from 'date-fns';

const notifIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertTriangle,
  legal: Scale,
  financial: DollarSign,
};

const notifColors = {
  info: 'text-blue-400',
  success: 'text-emerald-400',
  warning: 'text-amber-400',
  error: 'text-rose-400',
  legal: 'text-gold',
  financial: 'text-emerald-400',
};

export default function Header() {
  const navigate = useNavigate();
  const {
    user,
    notifications,
    unreadCount,
    markNotificationRead,
    markAllNotificationsRead,
    globalSearchQuery,
    setGlobalSearch,
    logout,
  } = useAppStore();

  const [showNotifs, setShowNotifs] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (globalSearchQuery.trim()) {
      navigate(`/caselaw?q=${encodeURIComponent(globalSearchQuery)}`);
    }
  };

  return (
    <header
      className="sticky top-0 z-40 flex items-center gap-4 px-6 h-16 border-b border-slate-800/60"
      style={{
        background: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search cases, laws, documents, entities..."
            value={globalSearchQuery}
            onChange={(e) => setGlobalSearch(e.target.value)}
            className="w-full bg-slate-900/60 border border-slate-700/60 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-gold/40 focus:ring-1 focus:ring-gold/20 transition-all"
          />
          {globalSearchQuery && (
            <button
              type="button"
              onClick={() => setGlobalSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </form>

      <div className="flex items-center gap-3 ml-auto">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => { setShowNotifs(!showNotifs); setShowUserMenu(false); }}
            className="relative p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-gold rounded-full animate-pulse" />
            )}
          </button>

          <AnimatePresence>
            {showNotifs && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-96 glass-card border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl z-50"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/40">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200">Notifications</h3>
                    {unreadCount > 0 && (
                      <p className="text-xs text-slate-500">{unreadCount} unread</p>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllNotificationsRead}
                      className="text-xs text-gold hover:text-gold/80 transition-colors"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-slate-500 text-sm">No notifications</div>
                  ) : (
                    notifications.map((notif) => {
                      const Icon = notifIcons[notif.type] || Info;
                      const colorClass = notifColors[notif.type] || 'text-slate-400';
                      return (
                        <div
                          key={notif.id}
                          onClick={() => {
                            markNotificationRead(notif.id);
                            if (notif.link) { navigate(notif.link); setShowNotifs(false); }
                          }}
                          className={clsx(
                            'flex gap-3 px-4 py-3 border-b border-slate-800/30 cursor-pointer hover:bg-slate-800/30 transition-colors',
                            !notif.read && 'bg-slate-800/20'
                          )}
                        >
                          <div className={clsx('flex-shrink-0 mt-0.5', colorClass)}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className={clsx('text-sm font-medium', notif.read ? 'text-slate-400' : 'text-slate-200')}>
                              {notif.title}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5">{notif.message}</p>
                            <p className="text-xs text-slate-600 mt-1">
                              {formatDistanceToNow(new Date(notif.createdAt), { addSuffix: true })}
                            </p>
                          </div>
                          {!notif.read && (
                            <div className="flex-shrink-0 w-2 h-2 bg-gold rounded-full mt-1.5" />
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Divider */}
        <div className="w-px h-6 bg-slate-700" />

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => { setShowUserMenu(!showUserMenu); setShowNotifs(false); }}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl hover:bg-slate-800/60 transition-all"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-slate-900 font-bold text-sm flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #D4AF37, #F5D87A)' }}
            >
              {user?.name?.charAt(0) ?? 'U'}
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-medium text-slate-200 leading-tight">{user?.name}</div>
              <div className="text-xs text-slate-500">{user?.role?.replace(/_/g, ' ')}</div>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>

          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-52 glass-card border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl z-50"
              >
                <div className="px-4 py-3 border-b border-slate-700/40">
                  <p className="text-sm font-semibold text-slate-200">{user?.name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                  {user?.barNumber && (
                    <p className="text-xs text-gold mt-0.5">Bar #{user.barNumber}</p>
                  )}
                </div>
                <div className="py-1">
                  {[
                    { icon: User, label: 'Profile', action: () => navigate('/settings') },
                    { icon: Settings, label: 'Settings', action: () => navigate('/settings') },
                    { icon: LogOut, label: 'Sign Out', action: logout, danger: true },
                  ].map((item) => (
                    <button
                      key={item.label}
                      onClick={() => { item.action(); setShowUserMenu(false); }}
                      className={clsx(
                        'w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                        item.danger
                          ? 'text-rose-400 hover:bg-rose-500/10'
                          : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                      )}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
