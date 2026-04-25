import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  User, Key, Bell, Palette, Link2, Download, Shield,
  CheckCircle, XCircle, AlertCircle, ChevronRight,
  Eye, EyeOff, Save,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { clsx } from 'clsx';
import { useAppStore } from '../store/appStore';

const sections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api', label: 'API Keys', icon: Key },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'integrations', label: 'Integrations', icon: Link2 },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'export', label: 'Export Data', icon: Download },
];

const themes = [
  { id: 'dark-gold', name: 'Dark Gold', primary: '#D4AF37', bg: '#020617' },
  { id: 'midnight-blue', name: 'Midnight Blue', primary: '#3B82F6', bg: '#020617' },
  { id: 'forest', name: 'Forest', primary: '#10B981', bg: '#020617' },
  { id: 'crimson', name: 'Crimson', primary: '#F43F5E', bg: '#020617' },
  { id: 'light', name: 'Light Mode', primary: '#0F172A', bg: '#F8FAFC' },
];

const integrations = [
  { name: 'Plaid (Banking)', status: 'connected', description: 'Bank accounts, transactions, net worth tracking', lastSync: '2 min ago' },
  { name: 'CourtListener', status: 'connected', description: 'Federal case law, PACER, court opinions', lastSync: '1 hour ago' },
  { name: 'PACER', status: 'connected', description: 'Federal court records and filings', lastSync: '30 min ago' },
  { name: 'OpenAI GPT-4', status: 'connected', description: 'AI motion drafting, legal analysis, research', lastSync: 'Active' },
  { name: 'Westlaw', status: 'error', description: 'Legal research, case law database', lastSync: 'Failed 2 hours ago' },
  { name: 'LexisNexis', status: 'disconnected', description: 'Legal research and news', lastSync: 'Never' },
  { name: 'Stripe', status: 'connected', description: 'Billing and payment processing', lastSync: '5 min ago' },
  { name: 'DocuSign', status: 'disconnected', description: 'Electronic signature workflows', lastSync: 'Never' },
];

const apiKeys = [
  { name: 'OpenAI API Key', key: 'sk-proj-...Xm9K', created: '2024-01-15', lastUsed: 'Today', status: 'active' },
  { name: 'CourtListener Token', key: 'cl_live_...7Hqp', created: '2024-02-20', lastUsed: 'Today', status: 'active' },
  { name: 'Plaid Client Secret', key: 'plaid_...4KQw', created: '2024-03-10', lastUsed: 'Today', status: 'active' },
  { name: 'Legacy Westlaw Key', key: 'wl_...9nBx', created: '2023-11-01', lastUsed: '2 weeks ago', status: 'inactive' },
];

const statusIconMap: Record<string, React.ElementType> = {
  connected: CheckCircle,
  disconnected: XCircle,
  error: AlertCircle,
};

const statusColorMap: Record<string, string> = {
  connected: 'text-emerald-400',
  disconnected: 'text-slate-500',
  error: 'text-rose-400',
};

export default function Settings() {
  const { user, theme, setTheme, sidebarCollapsed } = useAppStore();
  const [activeSection, setActiveSection] = useState('profile');
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-slate-500 text-sm mt-1">Manage your account, integrations, and preferences</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Nav */}
        <Card padding="sm">
          <div className="space-y-0.5">
            {sections.map((s) => {
              const Icon = s.icon;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all',
                    activeSection === s.id
                      ? 'bg-gold/10 text-gold'
                      : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{s.label}</span>
                  {activeSection === s.id && <ChevronRight className="w-3.5 h-3.5 ml-auto" />}
                </button>
              );
            })}
          </div>
        </Card>

        {/* Content */}
        <div className="xl:col-span-3">
          <motion.div
            key={activeSection}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            {activeSection === 'profile' && (
              <Card padding="lg">
                <CardHeader title="Profile" subtitle="Your personal and professional information" />
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-gold/20 border border-gold/30 flex items-center justify-center text-2xl font-bold text-gold">
                    {user?.name?.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-200">{user?.name}</p>
                    <p className="text-sm text-slate-500">{user?.role}</p>
                    <Button variant="outline" size="sm" className="mt-2">Change Photo</Button>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { label: 'Full Name', value: user?.name ?? '', type: 'text' },
                    { label: 'Email', value: user?.email ?? '', type: 'email' },
                    { label: 'Bar Number', value: 'NY-2019-87654', type: 'text' },
                    { label: 'Jurisdiction', value: 'New York, Federal', type: 'text' },
                    { label: 'Law Firm', value: 'SintraPrime Law & Financial Group', type: 'text' },
                    { label: 'Phone', value: '+1 (212) 555-0192', type: 'tel' },
                  ].map((field) => (
                    <div key={field.label}>
                      <label className="text-xs text-slate-500 font-medium uppercase block mb-1">{field.label}</label>
                      <input
                        type={field.type}
                        defaultValue={field.value}
                        className="input-dark py-2 text-sm"
                      />
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex gap-2">
                  <Button onClick={handleSave} icon={saved ? CheckCircle : Save}>
                    {saved ? 'Saved!' : 'Save Changes'}
                  </Button>
                </div>
              </Card>
            )}

            {activeSection === 'api' && (
              <Card padding="lg">
                <CardHeader title="API Key Management" subtitle="Manage your service API keys" />
                <div className="space-y-3">
                  {apiKeys.map((apiKey, i) => (
                    <div key={i} className="flex items-center gap-4 p-3.5 bg-slate-800/30 rounded-xl border border-slate-700/30">
                      <Key className="w-5 h-5 text-gold flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="text-sm font-medium text-slate-200">{apiKey.name}</p>
                          <Badge variant={apiKey.status === 'active' ? 'green' : 'slate'} size="sm">{apiKey.status}</Badge>
                        </div>
                        <div className="font-mono text-xs text-slate-500">
                          {showKey[apiKey.name] ? 'sk-proj-[HIDDEN_FOR_SECURITY]' : apiKey.key}
                        </div>
                        <p className="text-[10px] text-slate-600 mt-1">Created {apiKey.created} - Last used {apiKey.lastUsed}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setShowKey((prev) => ({ ...prev, [apiKey.name]: !prev[apiKey.name] }))}
                          className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors"
                        >
                          {showKey[apiKey.name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                        <Button variant="danger" size="sm">Revoke</Button>
                      </div>
                    </div>
                  ))}
                </div>
                <Button icon={Key} variant="outline" className="mt-4">Generate New API Key</Button>
              </Card>
            )}

            {activeSection === 'appearance' && (
              <Card padding="lg">
                <CardHeader title="Appearance" subtitle="Customize the look and feel" />
                <div>
                  <p className="text-sm font-semibold text-slate-300 mb-3">Theme</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                    {themes.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTheme(t.id as Parameters<typeof setTheme>[0])}
                        className={clsx(
                          'p-3 rounded-xl border text-left transition-all',
                          theme === t.id
                            ? 'border-gold/60 bg-gold/5'
                            : 'border-slate-700/40 hover:border-slate-600/60'
                        )}
                      >
                        <div
                          className="w-full h-8 rounded-lg mb-2"
                          style={{
                            background: `linear-gradient(135deg, ${t.bg} 0%, ${t.primary}40 100%)`,
                            border: `2px solid ${t.primary}`,
                          }}
                        />
                        <p className="text-xs font-medium text-slate-300">{t.name}</p>
                        {theme === t.id && <Badge variant="gold" size="sm" className="mt-1">Active</Badge>}
                      </button>
                    ))}
                  </div>

                  <p className="text-sm font-semibold text-slate-300 mb-3">Interface</p>
                  <div className="space-y-3">
                    {[
                      { label: 'Compact Sidebar', desc: 'Show icon-only sidebar by default', value: sidebarCollapsed },
                      { label: 'Reduce Motion', desc: 'Minimize animations for accessibility', value: false },
                      { label: 'High Contrast', desc: 'Increase text contrast ratios', value: false },
                      { label: 'Dense Tables', desc: 'Smaller row height for data tables', value: false },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-xl">
                        <div>
                          <p className="text-sm text-slate-200">{item.label}</p>
                          <p className="text-xs text-slate-500">{item.desc}</p>
                        </div>
                        <div
                          className={clsx(
                            'w-10 h-5 rounded-full relative cursor-pointer transition-colors',
                            item.value ? 'bg-gold' : 'bg-slate-700'
                          )}
                        >
                          <div
                            className={clsx(
                              'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
                              item.value ? 'left-5' : 'left-0.5'
                            )}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {activeSection === 'integrations' && (
              <Card padding="lg">
                <CardHeader title="Integrations" subtitle="Connected services and external APIs" />
                <div className="space-y-3">
                  {integrations.map((integration, i) => {
                    const StatusIcon = statusIconMap[integration.status] ?? XCircle;
                    return (
                      <div key={i} className="flex items-center gap-4 p-3.5 bg-slate-800/30 rounded-xl border border-slate-700/30">
                        <div className="w-9 h-9 rounded-xl bg-slate-700/50 flex items-center justify-center">
                          <Link2 className="w-4 h-4 text-slate-400" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-0.5">
                            <p className="text-sm font-medium text-slate-200">{integration.name}</p>
                            <StatusIcon className={clsx('w-3.5 h-3.5', statusColorMap[integration.status])} />
                          </div>
                          <p className="text-xs text-slate-500">{integration.description}</p>
                          <p className="text-[10px] text-slate-600 mt-0.5">Last sync: {integration.lastSync}</p>
                        </div>
                        <Button
                          variant={integration.status === 'connected' ? 'outline' : 'primary'}
                          size="sm"
                        >
                          {integration.status === 'connected'
                            ? 'Manage'
                            : integration.status === 'error'
                            ? 'Reconnect'
                            : 'Connect'}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {activeSection === 'notifications' && (
              <Card padding="lg">
                <CardHeader title="Notifications" subtitle="Control what alerts and emails you receive" />
                <div className="space-y-4">
                  {[
                    { cat: 'Legal', items: ['Case deadline reminders (7 days)', 'New case law matching saved searches', 'Court hearing reminders', 'Filing confirmation receipts'] },
                    { cat: 'Financial', items: ['Credit score changes', 'Large transactions (over $1,000)', 'Monthly financial summary', 'New funding opportunities matched'] },
                    { cat: 'AI Parliament', items: ['New decision session started', 'Decision requires human override', 'Weekly decision digest'] },
                    { cat: 'System', items: ['Integration connection errors', 'New features and updates', 'Security alerts'] },
                  ].map((group) => (
                    <div key={group.cat}>
                      <p className="text-xs font-semibold text-slate-400 uppercase mb-2">{group.cat}</p>
                      <div className="space-y-2">
                        {group.items.map((item) => (
                          <div key={item} className="flex items-center justify-between py-2 border-b border-slate-800/60">
                            <p className="text-sm text-slate-300">{item}</p>
                            <div className="flex items-center gap-4">
                              {['Email', 'Push'].map((method) => (
                                <label key={method} className="flex items-center gap-1.5 cursor-pointer">
                                  <input type="checkbox" defaultChecked className="w-3.5 h-3.5 accent-amber-500" />
                                  <span className="text-xs text-slate-500">{method}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {activeSection === 'security' && (
              <Card padding="lg">
                <CardHeader title="Security" subtitle="Account security settings" />
                <div className="space-y-4">
                  {[
                    { label: 'Two-Factor Authentication', desc: 'Add an extra layer of security via authenticator app', enabled: true },
                    { label: 'Login Alerts', desc: 'Email on new device login', enabled: true },
                    { label: 'Session Timeout', desc: 'Auto-logout after 2 hours of inactivity', enabled: true },
                    { label: 'IP Allowlist', desc: 'Restrict login to specific IP ranges', enabled: false },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Shield className={clsx('w-5 h-5', item.enabled ? 'text-emerald-400' : 'text-slate-500')} />
                        <div>
                          <p className="text-sm font-medium text-slate-200">{item.label}</p>
                          <p className="text-xs text-slate-500">{item.desc}</p>
                        </div>
                      </div>
                      <Badge variant={item.enabled ? 'green' : 'slate'}>{item.enabled ? 'Enabled' : 'Disabled'}</Badge>
                    </div>
                  ))}
                  <Button variant="outline" className="mt-2">Change Password</Button>
                </div>
              </Card>
            )}

            {activeSection === 'export' && (
              <Card padding="lg">
                <CardHeader title="Export All Data" subtitle="Download a complete copy of your SintraPrime data" />
                <div className="space-y-3">
                  {[
                    { name: 'All Cases & Documents', desc: 'Complete case files, motions, and evidence', size: '~245 MB', format: 'ZIP' },
                    { name: 'Financial Records', desc: 'Transactions, portfolio, credit history', size: '~12 MB', format: 'CSV' },
                    { name: 'Entity Documents', desc: 'LLC agreements, trust docs, corporate records', size: '~58 MB', format: 'ZIP' },
                    { name: 'Case Law Library', desc: 'All saved and bookmarked case law', size: '~3 MB', format: 'JSON' },
                    { name: 'AI Parliament History', desc: 'All decisions, debates, and outcomes', size: '~800 KB', format: 'JSON' },
                    { name: 'Complete Data Export', desc: 'Everything including account data', size: '~320 MB', format: 'ZIP' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-4 p-3.5 bg-slate-800/30 rounded-xl">
                      <Download className="w-5 h-5 text-gold flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-200">{item.name}</p>
                        <p className="text-xs text-slate-500">{item.desc}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="slate" size="sm">{item.format}</Badge>
                          <span className="text-[10px] text-slate-600">{item.size}</span>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" icon={Download}>Export</Button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-600 mt-4">All data is encrypted before export. Links expire after 24 hours.</p>
              </Card>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
