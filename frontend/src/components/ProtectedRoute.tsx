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
 *   - Demo mode is active (allows unauthenticated access for presentations)
 *
 * Security note: even in demo mode we always wait for the auth check to
 * resolve first. This prevents instant bypass via localStorage manipulation —
 * a real authenticated user's session will be found and used automatically.
 * The backend independently enforces auth on all sensitive endpoints.
 *
 * On redirect to /, passes `state: { openAuth: true }` so the landing
 * page opens the sign-in modal automatically.
 */
export function ProtectedRoute({ children }: Props) {
  const { user, loading: authLoading } = useAuth();
  const { isDemoMode } = useDemoMode();

  // Always wait for auth to resolve — prevents instant localStorage bypass
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg">
        <div className="w-1.5 h-1.5 rounded-full bg-theme-text-muted animate-pulse" />
      </div>
    );
  }

  // Authenticated users always get in
  if (user) {
    return <>{children}</>;
  }

  // Demo mode allows unauthenticated access (for presentations/demos).
  // Backend endpoints still require auth — demo mode only affects UI data source.
  if (isDemoMode) {
    return <>{children}</>;
  }

  // Not authenticated and not in demo mode → back to landing, open sign-in
  return <Navigate to="/" replace state={{ openAuth: true }} />;
}
