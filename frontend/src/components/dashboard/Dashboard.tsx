import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, ArrowLeft, Clock, CheckCircle2, XCircle, Loader2,
  PauseCircle, FlaskConical, Radio, Search, Trash2,
  Activity, TrendingUp, BarChart2, LogOut,
} from 'lucide-react';
import { engagementsApi, type Engagement } from '../../lib/apiClient';
import { useDemoMode } from '../../context/DemoModeContext';
import { ToastProvider } from '../ui/Toast';
import { useAuth } from '../../context/AuthContext';
import NewEngagementModal from './NewEngagementModal';
import PipelineView from './PipelineView';
import ResultsPanel from './ResultsPanel';

type DashView = 'list' | 'pipeline' | 'results';

const STATUS_CONFIG: Record<string, { label: string; color: string; Icon: React.ElementType }> = {
  draft:     { label: 'Draft',     color: 'text-theme-text-muted', Icon: Clock },
  running:   { label: 'Running',   color: 'text-blue-400',          Icon: Loader2 },
  paused:    { label: 'Paused',    color: 'text-amber-400',         Icon: PauseCircle },
  completed: { label: 'Completed', color: 'text-green-400',         Icon: CheckCircle2 },
  failed:    { label: 'Failed',    color: 'text-red-400',           Icon: XCircle },
};

// ── Skeleton card ─────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="w-full flex items-center justify-between px-5 py-4 border border-theme-border rounded-xl animate-pulse">
      <div className="flex-1 space-y-2 min-w-0">
        <div className="h-3.5 bg-theme-border rounded w-48" />
        <div className="h-2.5 bg-theme-border rounded w-72 opacity-60" />
      </div>
      <div className="flex items-center gap-4 flex-shrink-0 ml-4">
        <div className="hidden md:flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-16 h-1 bg-theme-border rounded-full" />
          ))}
        </div>
        <div className="h-3 w-16 bg-theme-border rounded" />
        <div className="h-3 w-20 bg-theme-border rounded hidden lg:block" />
      </div>
    </div>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────
function StatsBar({ engagements }: { engagements: Engagement[] }) {
  const total     = engagements.length;
  const running   = engagements.filter((e) => e.status === 'running').length;
  const completed = engagements.filter((e) => e.status === 'completed').length;
  const failed    = engagements.filter((e) => e.status === 'failed').length;

  const stats = [
    { label: 'Total',     value: total,     icon: BarChart2,  color: 'text-theme-text-muted' },
    { label: 'Running',   value: running,   icon: Activity,   color: 'text-blue-400' },
    { label: 'Completed', value: completed, icon: TrendingUp, color: 'text-green-400' },
    { label: 'Failed',    value: failed,    icon: XCircle,    color: 'text-red-400', hide: failed === 0 },
  ] as const;

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {stats.map((s) => {
        if ((s as { hide?: boolean }).hide) return null;
        const Icon = s.icon;
        return (
          <div
            key={s.label}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-theme-border bg-theme-surface/40 text-[10px] font-mono"
          >
            <Icon className={`w-3 h-3 ${s.color}`} />
            <span className={`font-semibold ${s.color}`}>{s.value}</span>
            <span className="text-theme-text-muted">{s.label}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();
  const { isDemoMode } = useDemoMode();
  const { user, signOut } = useAuth();
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selected, setSelected] = useState<Engagement | null>(null);
  const [dashView, setDashView] = useState<DashView>('list');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  useEffect(() => {
    engagementsApi
      .list()
      .then(setEngagements)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Poll running engagement every 5s to pick up status changes
  useEffect(() => {
    if (!selected || !['running', 'paused'].includes(selected.status)) return;
    const id = setInterval(async () => {
      try {
        const fresh = await engagementsApi.get(selected.id);
        setSelected(fresh);
        setEngagements((prev) => prev.map((e) => (e.id === fresh.id ? fresh : e)));
        if (fresh.status === 'completed') setDashView('results');
      } catch {}
    }, 5000);
    return () => clearInterval(id);
  }, [selected?.id, selected?.status]);

  const handleCreated = (engagement: Engagement) => {
    setEngagements((prev) => [engagement, ...prev]);
    setSelected(engagement);
    setDashView('pipeline');
    setShowModal(false);
  };

  const openEngagement = async (engagement: Engagement) => {
    try {
      const fresh = await engagementsApi.get(engagement.id);
      setSelected(fresh);
      setDashView(fresh.status === 'completed' ? 'results' : 'pipeline');
    } catch {
      setSelected(engagement);
      setDashView(engagement.status === 'completed' ? 'results' : 'pipeline');
    }
  };

  const handleEngagementUpdate = (updated: Engagement) => {
    setSelected(updated);
    setEngagements((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    if (updated.status === 'completed') setDashView('results');
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await engagementsApi.delete(id);
      setEngagements((prev) => prev.filter((e) => e.id !== id));
      if (selected?.id === id) {
        setSelected(null);
        setDashView('list');
      }
    } catch {}
    setDeletingId(null);
    setConfirmDeleteId(null);
  };

  // Results tab is available whenever the engagement has started (not draft)
  const canShowResults = selected && selected.status !== 'draft';

  return (
    <ToastProvider>
      <div className="min-h-screen bg-theme-bg text-theme-text">
        {/* Dashboard Navbar */}
        <nav
          className="fixed top-0 w-full z-50 backdrop-blur-md border-b border-theme-border"
          style={{ backgroundColor: 'var(--color-nav-solid)' }}
        >
          <div className="max-w-7xl mx-auto px-4 md:px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => navigate('/')}
                  className="flex items-center gap-1.5 text-[11px] font-mono text-theme-text-muted
                             hover:text-theme-text transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  BACK
                </button>
                <div className="w-px h-4 bg-theme-border" />
                <h1 className="text-sm font-bold tracking-tight">KEEN</h1>
                <span className="text-[10px] font-mono text-theme-text-muted hidden sm:block">
                  DASHBOARD
                </span>
              </div>

              <div className="flex items-center gap-3">
                {/* Breadcrumb */}
                {dashView !== 'list' && selected && (
                  <div className="hidden md:flex items-center gap-1.5 text-[10px] font-mono text-theme-text-muted">
                    <button
                      onClick={() => setDashView('list')}
                      className="hover:text-theme-text transition-colors"
                    >
                      Engagements
                    </button>
                    <span>/</span>
                    <span className="text-theme-text truncate max-w-32">
                      {selected.company_name}
                    </span>
                    {dashView === 'results' && (
                      <>
                        <span>/</span>
                        <span className="text-green-400">Results</span>
                      </>
                    )}
                  </div>
                )}

                {/* Demo/Live badge */}
                <div
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]
                               font-mono font-semibold border ${
                    isDemoMode
                      ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                      : 'border-green-500/40 bg-green-500/10 text-green-400'
                  }`}
                >
                  {isDemoMode ? (
                    <FlaskConical className="w-3 h-3" />
                  ) : (
                    <Radio className="w-3 h-3 animate-pulse" />
                  )}
                  {isDemoMode ? 'DEMO' : 'LIVE'}
                </div>

                {/* User email chip */}
                {user?.email && (
                  <span className="hidden md:block text-[10px] font-mono text-theme-text-muted truncate max-w-[160px]">
                    {user.email}
                  </span>
                )}

                {/* Sign out */}
                <button
                  onClick={() => signOut()}
                  title="Sign out"
                  className="p-1.5 rounded-lg text-theme-text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>

                {/* New engagement button */}
                <button
                  onClick={() => setShowModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-theme-text text-theme-bg
                             text-[10px] font-mono font-semibold rounded-lg hover:opacity-90 transition-opacity"
                >
                  <Plus className="w-3.5 h-3.5" />
                  NEW
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <div className="max-w-7xl mx-auto px-4 md:px-6 pt-20 pb-12">

          {/* ── List view ── */}
          {dashView === 'list' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Engagements</h2>
                  <p className="text-xs text-theme-text-muted font-mono mt-0.5">
                    {isDemoMode
                      ? 'Simulation mode — pipelines use fixture data'
                      : 'Live mode — pipelines connect to enterprise data sources'}
                  </p>
                </div>
                {!loading && engagements.length > 0 && (
                  <StatsBar engagements={engagements} />
                )}
              </div>

              {/* Skeleton while loading */}
              {loading && (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => <SkeletonCard key={i} />)}
                </div>
              )}

              {/* Empty state */}
              {!loading && engagements.length === 0 && (
                <div className="border border-dashed border-theme-border rounded-xl p-12 text-center space-y-4">
                  <Search className="w-8 h-8 text-theme-text-muted mx-auto" />
                  <div>
                    <p className="text-sm font-semibold">No engagements yet</p>
                    <p className="text-xs text-theme-text-muted mt-1">
                      Start your first due diligence pipeline
                    </p>
                  </div>
                  <button
                    onClick={() => setShowModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-theme-text text-theme-bg
                               text-xs font-mono font-semibold rounded-lg hover:opacity-90 transition-opacity"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    NEW ENGAGEMENT
                  </button>
                </div>
              )}

              {/* Engagement list */}
              {!loading && engagements.length > 0 && (
                <div className="space-y-2">
                  {engagements.map((e) => {
                    const cfg = STATUS_CONFIG[e.status] ?? STATUS_CONFIG.draft;
                    const isDemo = e.config?.demo_mode as boolean | undefined;
                    const isConfirming = confirmDeleteId === e.id;
                    const isDeleting = deletingId === e.id;
                    return (
                      <div
                        key={e.id}
                        className="w-full flex items-center justify-between px-5 py-4 border border-theme-border
                                   rounded-xl hover:border-theme-text/30 hover:bg-theme-border/20
                                   transition-all group"
                      >
                        {/* Clickable main area */}
                        <button
                          onClick={() => openEngagement(e)}
                          className="flex-1 flex items-center gap-4 text-left min-w-0"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold truncate">{e.company_name}</p>
                              {isDemo !== undefined && (
                                <span
                                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded border flex-shrink-0 ${
                                    isDemo
                                      ? 'border-amber-500/30 text-amber-400 bg-amber-500/10'
                                      : 'border-green-500/30 text-green-400 bg-green-500/10'
                                  }`}
                                >
                                  {isDemo ? 'DEMO' : 'LIVE'}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5 truncate">
                              {String(e.config?.engagement_type ?? 'full_diligence').replace(/_/g, ' ')}
                              {e.pe_firm && ` · ${e.pe_firm}`}
                              {e.deal_size && ` · ${e.deal_size}`}
                            </p>
                          </div>
                        </button>

                        {/* Right: progress bars + status + date + delete */}
                        <div className="flex items-center gap-4 flex-shrink-0 ml-4">
                          {e.agent_runs && e.agent_runs.length > 0 && (
                            <div className="hidden md:flex items-center gap-1">
                              {e.agent_runs.map((run) => (
                                <div
                                  key={run.id}
                                  className="w-16 h-1 bg-theme-border rounded-full overflow-hidden"
                                >
                                  <div
                                    className={`h-full rounded-full ${
                                      run.status === 'completed' ? 'bg-green-500' :
                                      run.status === 'running'   ? 'bg-blue-500' :
                                      run.status === 'failed'    ? 'bg-red-500'  : 'bg-theme-border'
                                    }`}
                                    style={{ width: `${run.progress_pct ?? 0}%` }}
                                  />
                                </div>
                              ))}
                            </div>
                          )}
                          <div className={`flex items-center gap-1.5 text-[11px] font-mono ${cfg.color}`}>
                            <cfg.Icon
                              className={`w-3.5 h-3.5 ${e.status === 'running' ? 'animate-spin' : ''}`}
                            />
                            {cfg.label}
                          </div>
                          <p className="text-[10px] font-mono text-theme-text-muted hidden lg:block">
                            {new Date(e.created_at).toLocaleDateString()}
                          </p>

                          {/* Delete */}
                          {isConfirming ? (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => handleDelete(e.id)}
                                disabled={isDeleting}
                                className="px-2 py-1 text-[10px] font-mono bg-red-500/20 border border-red-500/40
                                           text-red-400 rounded hover:bg-red-500/30 transition-colors disabled:opacity-50"
                              >
                                {isDeleting ? <Loader2 className="w-3 h-3 animate-spin" /> : 'DELETE'}
                              </button>
                              <button
                                onClick={() => setConfirmDeleteId(null)}
                                className="px-2 py-1 text-[10px] font-mono text-theme-text-muted
                                           hover:text-theme-text transition-colors"
                              >
                                CANCEL
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={(ev) => { ev.stopPropagation(); setConfirmDeleteId(e.id); }}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg
                                         hover:bg-red-500/10 text-theme-text-muted hover:text-red-400
                                         transition-all"
                              title="Delete engagement"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ── Pipeline / Results view ── */}
          {(dashView === 'pipeline' || dashView === 'results') && selected && (
            <div className="space-y-4">
              {/* Back + tab switcher */}
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setDashView('list')}
                  className="flex items-center gap-1.5 text-[11px] font-mono text-theme-text-muted
                             hover:text-theme-text transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  ALL ENGAGEMENTS
                </button>

                {/* Tab bar — available as soon as the engagement has started */}
                {canShowResults && (
                  <div className="flex items-center gap-1 border border-theme-border rounded-lg p-0.5">
                    <button
                      onClick={() => setDashView('pipeline')}
                      className={`px-3 py-1 text-[10px] font-mono rounded-md transition-colors ${
                        dashView === 'pipeline'
                          ? 'bg-theme-text text-theme-bg font-semibold'
                          : 'text-theme-text-muted hover:text-theme-text'
                      }`}
                    >
                      PIPELINE
                    </button>
                    <button
                      onClick={() => setDashView('results')}
                      className={`flex items-center gap-1.5 px-3 py-1 text-[10px] font-mono rounded-md transition-colors ${
                        dashView === 'results'
                          ? 'bg-theme-text text-theme-bg font-semibold'
                          : 'text-theme-text-muted hover:text-theme-text'
                      }`}
                    >
                      RESULTS
                      {/* Live pulse dot when pipeline still running */}
                      {selected.status === 'running' && (
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                      )}
                    </button>
                  </div>
                )}
              </div>

              {dashView === 'pipeline' && (
                <PipelineView
                  engagement={selected}
                  onEngagementUpdate={handleEngagementUpdate}
                />
              )}
              {dashView === 'results' && (
                <ResultsPanel engagement={selected} />
              )}
            </div>
          )}
        </div>

        {showModal && (
          <NewEngagementModal
            onClose={() => setShowModal(false)}
            onCreated={handleCreated}
          />
        )}
      </div>
    </ToastProvider>
  );
}
