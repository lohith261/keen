import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDemoMode } from '../context/DemoModeContext';

interface Props {
  children: React.ReactNode;
}

/**
 * Guards the /dashboard route.
 *
 * Access is allowed when:
 *   - The user is authenticated (Supabase session), OR
 *   - Demo mode is active (no credentials needed)
 *
 * While auth is resolving (first render), shows a loading dot unless
 * demo mode is already active — in that case, proceed immediately.
 *
 * On redirect to /, passes `state: { openAuth: true }` so the landing
 * page opens the sign-in modal automatically.
 */
export function ProtectedRoute({ children }: Props) {
  const { user, loading: authLoading } = useAuth();
  const { isDemoMode } = useDemoMode();

  // Demo mode bypasses auth entirely — show dashboard immediately
  if (isDemoMode) {
    return <>{children}</>;
  }

  // Auth is still resolving — hold on a moment
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg">
        <div className="w-1.5 h-1.5 rounded-full bg-theme-text-muted animate-pulse" />
      </div>
    );
  }

  // Not authenticated and not in demo mode → back to landing, open sign-in
  if (!user) {
    return <Navigate to="/" replace state={{ openAuth: true }} />;
  }

  return <>{children}</>;
}
