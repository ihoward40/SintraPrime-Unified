import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Lock, Mail, Scale } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { login, type LoginResponse } from '../api/auth';
import { useAppStore, type User } from '../store/appStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUser } = useAppStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [challengeToken, setChallengeToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response: LoginResponse = await login({
        email: email.trim().toLowerCase(),
        password,
        ...(challengeToken ? { mfa_code: mfaCode } : {}),
      });

      if (response.requires_mfa && response.mfa_challenge_token) {
        setChallengeToken(response.mfa_challenge_token);
        setLoading(false);
        return;
      }

      setUser({
        id: response.user_id,
        name: email.split('@')[0],
        email,
        role: response.role as User['role'],
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

      navigate('/documents', { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
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
        className="w-full max-w-md"
      >
        <Card className="p-8" gold>
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gold to-amber-300 flex items-center justify-center mb-4 shadow-lg">
              <Scale className="w-7 h-7 text-slate-900" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">SintraPrime</h1>
            <p className="text-sm text-slate-500 mt-1">Sign in to the Document Vault</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-200 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {!challengeToken ? (
              <>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-300" htmlFor="email">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
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
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300" htmlFor="mfa">MFA Code</label>
                <input
                  id="mfa"
                  type="text"
                  inputMode="numeric"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  required
                  maxLength={6}
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30"
                  placeholder="000000"
                />
              </div>
            )}

            <Button
              type="submit"
              variant="gold"
              fullWidth
              loading={loading}
              disabled={loading}
            >
              {challengeToken ? 'Verify MFA' : 'Sign In'}
            </Button>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
