import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/appStore';
import { hasValidToken } from '../api/auth';

/**
 * Boot-time auth initialization.
 *
 * - If a valid access token exists in localStorage, mark the user as authenticated.
 * - If not, redirect unauthenticated users from protected routes to /login.
 *
 * This is intentionally minimal: we do not decode the JWT client-side.
 * The first API call will enforce auth server-side.
 */
export function useAuthInit({ requireAuth = true }: { requireAuth?: boolean } = {}) {
  const navigate = useNavigate();
  const { isAuthenticated, setUser } = useAppStore();

  useEffect(() => {
    const tokenValid = hasValidToken();

    if (tokenValid && !isAuthenticated) {
      // Mark as authenticated; user details will be fetched by the first API call
      setUser({
        id: 'pending',
        name: '',
        email: '',
        role: 'attorney',
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
    }

    if (!tokenValid && requireAuth && isAuthenticated) {
      // Token expired or missing while on a protected route
      navigate('/login', { replace: true });
    }
  }, [navigate, requireAuth, isAuthenticated, setUser]);

  return { isAuthenticated };
}

export default useAuthInit;
