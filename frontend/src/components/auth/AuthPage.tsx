/**
 * AuthPage — login / sign-up screen.
 *
 * Matches the existing KEEN dark theme.
 * Tabs toggle between "Sign in" and "Create account".
 */

import { useState } from 'react';
import { Loader2, Mail, Lock, Eye, EyeOff, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import ThemeToggle from '../ThemeToggle';

export default function AuthPage() {
  const { signIn, signUp } = useAuth();
  const { theme } = useTheme();

  const [tab, setTab] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false); // email confirmation needed

  const reset = () => { setError(null); setConfirmed(false); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true);
    setError(null);

    if (tab === 'signin') {
      const { error: err } = await signIn(email, password);
      if (err) setError(err);
      // On success AuthContext will update → App re-renders to Dashboard
    } else {
      const { error: err, needsConfirmation } = await signUp(email, password);
      if (err) { setError(err); }
      else if (needsConfirmation) { setConfirmed(true); }
      // Otherwise session is live → App re-renders
    }
    setLoading(false);
  };

  // ── Email confirmation message ─────────────────────────────────────────────
  if (confirmed) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-theme-bg px-4"
        data-theme={theme}
      >
        <div className="w-full max-w-sm text-center space-y-4">
          <CheckCircle2 className="w-10 h-10 text-green-400 mx-auto" />
          <h2 className="text-lg font-semibold text-theme-text">Check your email</h2>
          <p className="text-sm text-theme-text-muted">
            We sent a confirmation link to <span className="text-theme-text font-mono">{email}</span>.
            Click the link to activate your account then come back to sign in.
          </p>
          <button
            onClick={() => { setTab('signin'); setConfirmed(false); }}
            className="text-[11px] font-mono text-theme-text-muted hover:text-theme-text underline transition-colors"
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  // ── Main form ──────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen flex flex-col bg-theme-bg"
      data-theme={theme}
    >
      {/* Minimal nav bar */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-theme-border">
        <span className="text-sm font-bold tracking-tight text-theme-text">KEEN</span>
        <ThemeToggle />
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm space-y-6">
          {/* Header */}
          <div className="text-center space-y-1">
            <h1 className="text-xl font-bold text-theme-text">
              {tab === 'signin' ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="text-xs text-theme-text-muted font-mono">
              {tab === 'signin'
                ? 'Sign in to access your due diligence workspace'
                : 'Start running intelligent due diligence pipelines'}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex items-center gap-1 p-0.5 border border-theme-border rounded-xl">
            {(['signin', 'signup'] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); reset(); }}
                className={`flex-1 py-2 text-[11px] font-mono font-semibold rounded-lg transition-colors ${
                  tab === t
                    ? 'bg-theme-text text-theme-bg'
                    : 'text-theme-text-muted hover:text-theme-text'
                }`}
              >
                {t === 'signin' ? 'SIGN IN' : 'CREATE ACCOUNT'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Email */}
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-theme-text-muted pointer-events-none" />
              <input
                type="email"
                autoComplete="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); reset(); }}
                className="w-full pl-9 pr-4 py-2.5 text-sm font-mono bg-theme-surface border border-theme-border
                           rounded-xl text-theme-text placeholder:text-theme-text-muted
                           focus:outline-none focus:border-theme-text/50 transition-colors"
              />
            </div>

            {/* Password */}
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-theme-text-muted pointer-events-none" />
              <input
                type={showPw ? 'text' : 'password'}
                autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
                placeholder={tab === 'signin' ? 'Password' : 'Create a password'}
                value={password}
                onChange={(e) => { setPassword(e.target.value); reset(); }}
                className="w-full pl-9 pr-10 py-2.5 text-sm font-mono bg-theme-surface border border-theme-border
                           rounded-xl text-theme-text placeholder:text-theme-text-muted
                           focus:outline-none focus:border-theme-text/50 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-muted hover:text-theme-text transition-colors"
              >
                {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Error */}
            {error && (
              <p className="text-[11px] font-mono text-red-400 px-1">{error}</p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-theme-text text-theme-bg
                         text-[11px] font-mono font-semibold rounded-xl
                         hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <>
                  {tab === 'signin' ? 'SIGN IN' : 'CREATE ACCOUNT'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Footer note */}
          <p className="text-center text-[10px] text-theme-text-muted font-mono">
            {tab === 'signin' ? (
              <>No account?{' '}
                <button onClick={() => { setTab('signup'); reset(); }} className="underline hover:text-theme-text transition-colors">
                  Create one →
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => { setTab('signin'); reset(); }} className="underline hover:text-theme-text transition-colors">
                  Sign in →
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
