import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export type Theme = 'dark' | 'light' | 'midnight' | 'corporate' | 'emerald';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'legal' | 'financial';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  link?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'attorney' | 'client' | 'financial_manager';
  avatar?: string;
  firm?: string;
  barNumber?: string;
  preferences: UserPreferences;
}

export interface UserPreferences {
  theme: Theme;
  sidebarCollapsed: boolean;
  defaultLandingPage: string;
  emailNotifications: boolean;
  smsNotifications: boolean;
  showTutorials: boolean;
  dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
  currency: 'USD' | 'EUR' | 'GBP';
  timezone: string;
}

export interface IntegrationStatus {
  name: string;
  id: string;
  connected: boolean;
  lastSync?: string;
  status: 'active' | 'error' | 'disconnected' | 'pending';
  accountInfo?: string;
}

interface AppState {
  // User
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // UI State
  theme: Theme;
  sidebarCollapsed: boolean;
  activeModal: string | null;
  globalSearchQuery: string;
  
  // Notifications
  notifications: Notification[];
  unreadCount: number;
  
  // Integrations
  integrations: IntegrationStatus[];
  
  // Actions
  setUser: (user: User | null) => void;
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
  setGlobalSearch: (query: string) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  clearNotifications: () => void;
  updateIntegration: (id: string, status: Partial<IntegrationStatus>) => void;
  logout: () => void;
}

const defaultUser: User = {
  id: 'user-001',
  name: 'Marcus A. Sintra',
  email: 'marcus@sintraprime.com',
  role: 'admin',
  firm: 'SintraPrime Law & Financial Group',
  barNumber: 'CA-123456',
  preferences: {
    theme: 'dark',
    sidebarCollapsed: false,
    defaultLandingPage: '/dashboard',
    emailNotifications: true,
    smsNotifications: true,
    showTutorials: false,
    dateFormat: 'MM/DD/YYYY',
    currency: 'USD',
    timezone: 'America/New_York',
  },
};

const defaultIntegrations: IntegrationStatus[] = [
  { name: 'Plaid', id: 'plaid', connected: true, lastSync: new Date().toISOString(), status: 'active', accountInfo: '5 accounts linked' },
  { name: 'CourtListener', id: 'courtlistener', connected: true, lastSync: new Date().toISOString(), status: 'active' },
  { name: 'PACER', id: 'pacer', connected: true, lastSync: new Date().toISOString(), status: 'active', accountInfo: 'Federal court access' },
  { name: 'DocuSign', id: 'docusign', connected: false, status: 'disconnected' },
  { name: 'Westlaw', id: 'westlaw', connected: true, lastSync: new Date().toISOString(), status: 'active' },
  { name: 'LexisNexis', id: 'lexisnexis', connected: false, status: 'disconnected' },
];

const defaultNotifications: Notification[] = [
  {
    id: 'notif-001',
    type: 'legal',
    title: 'Case Deadline Approaching',
    message: 'Motion due in Sintra v. State in 3 days',
    read: false,
    createdAt: new Date(Date.now() - 30 * 60000).toISOString(),
    link: '/cases',
  },
  {
    id: 'notif-002',
    type: 'financial',
    title: 'Credit Score Updated',
    message: 'Your score increased by 12 points to 742',
    read: false,
    createdAt: new Date(Date.now() - 2 * 3600000).toISOString(),
    link: '/financial',
  },
  {
    id: 'notif-003',
    type: 'success',
    title: 'Motion Filed Successfully',
    message: 'Motion to Dismiss in Case #2024-CV-1847 accepted',
    read: true,
    createdAt: new Date(Date.now() - 24 * 3600000).toISOString(),
  },
  {
    id: 'notif-004',
    type: 'info',
    title: 'New Funding Opportunity',
    message: 'SBA 7(a) loan program: up to $5M available',
    read: true,
    createdAt: new Date(Date.now() - 48 * 3600000).toISOString(),
    link: '/financial',
  },
];

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        user: defaultUser,
        isAuthenticated: true,
        isLoading: false,
        theme: 'dark',
        sidebarCollapsed: false,
        activeModal: null,
        globalSearchQuery: '',
        notifications: defaultNotifications,
        unreadCount: defaultNotifications.filter((n) => !n.read).length,
        integrations: defaultIntegrations,

        // Actions
        setUser: (user) => set({ user, isAuthenticated: !!user }),

        setTheme: (theme) => {
          set({ theme });
          document.documentElement.className = theme === 'light' ? 'light' : 'dark';
        },

        toggleSidebar: () =>
          set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

        setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

        openModal: (modalId) => set({ activeModal: modalId }),

        closeModal: () => set({ activeModal: null }),

        setGlobalSearch: (query) => set({ globalSearchQuery: query }),

        addNotification: (notification) => {
          const newNotif: Notification = {
            ...notification,
            id: crypto.randomUUID(),
            read: false,
            createdAt: new Date().toISOString(),
          };
          set((state) => ({
            notifications: [newNotif, ...state.notifications],
            unreadCount: state.unreadCount + 1,
          }));
        },

        markNotificationRead: (id) =>
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, read: true } : n
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          })),

        markAllNotificationsRead: () =>
          set((state) => ({
            notifications: state.notifications.map((n) => ({ ...n, read: true })),
            unreadCount: 0,
          })),

        clearNotifications: () => set({ notifications: [], unreadCount: 0 }),

        updateIntegration: (id, status) =>
          set((state) => ({
            integrations: state.integrations.map((i) =>
              i.id === id ? { ...i, ...status } : i
            ),
          })),

        logout: () => {
          localStorage.removeItem('sintraprime_token');
          localStorage.removeItem('sintraprime_refresh_token');
          set({ user: null, isAuthenticated: false });
          window.location.href = '/login';
        },
      }),
      {
        name: 'sintraprime-app-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
          user: state.user,
        }),
      }
    ),
    { name: 'SintraPrime AppStore' }
  )
);
