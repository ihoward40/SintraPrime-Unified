import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building2, Lock, Mail, Scale, User } from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { completeFirstRunSetup, type LoginResponse } from '../api/auth';
import { useAppStore } from '../store/appStore';

export default function SetupPage() {
  const navigate = useNavigate();
  const { setUser } = useAppStore();

  const [ownerName, setOwnerName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response: LoginResponse = await completeFirstRunSetup({
        owner_name: ownerName.trim(),
        email: email.trim().toLowerCase(),
        password,
        organization_name: organizationName.trim(),
      });

      setUser({
        id: response.user_id,
        name: ownerName.trim(),
        email: email.trim().toLowerCase(),
        role: 'admin',
        firm: organizationName.trim(),
        preferences: {
          theme: 'dark',
          sidebarCollapsed: false,
          defaultLandingPage: '/dashboard',
          emailNotifications: true,
          smsNotifications: false,
          showTutorials: false,
          dateFormat: 'MM/DD/YYYY',
          currency: 'USD',
          timezone: 'America/New_York',
        },
      });

      navigate('/dashboard', { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Setup failed';
      setError(message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-lg"
      >
        <Card className="p-8" gold>
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gold to-amber-300 flex items-center justify-center mb-4 shadow-lg">
              <Scale className="w-7 h-7 text-slate-900" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">First-Run Owner Setup</h1>
            <p className="text-sm text-slate-500 mt-1">Create the owner account for this installation</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-200 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300" htmlFor="owner-name">Owner name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="owner-name"
                  type="text"
                  value={ownerName}
                  onChange={(event) => setOwnerName(event.target.value)}
                  required
                  autoComplete="name"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                  placeholder="Owner name"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300" htmlFor="organization-name">Organization</label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="organization-name"
                  type="text"
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  required
                  autoComplete="organization"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                  placeholder="Organization name"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300" htmlFor="email">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                  placeholder="you@firm.com"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300" htmlFor="password">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={12}
                  autoComplete="new-password"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                  placeholder="Minimum 12 characters"
                />
              </div>
            </div>

            <Button type="submit" variant="gold" fullWidth loading={loading} disabled={loading}>
              Create Owner Account
            </Button>
          </form>

          <div className="mt-5 text-center text-sm text-slate-500">
            <Link to="/login" className="text-gold hover:text-amber-200">
              Return to sign in
            </Link>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
