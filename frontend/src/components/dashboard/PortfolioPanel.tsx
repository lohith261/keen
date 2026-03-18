import { useCallback, useEffect, useState } from 'react';
import {
  Activity, AlertTriangle, Calendar, CheckCircle2, ChevronDown, ChevronRight,
  Clock, Loader2, Play, Plus, ToggleLeft, ToggleRight, Trash2, TrendingDown,
  TrendingUp, XCircle,
} from 'lucide-react';

const BACKEND_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
const API_BASE = `${BACKEND_URL}/api/v1`;

interface MonitoringRun {
  id: string;
  schedule_id: string;
  engagement_id: string;
  status: string;
  deltas: Delta[] | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface Delta {
  metric: string;
  baseline: number;
  current: number;
  delta_abs: number;
  delta_pct: number;
  severity: 'info' | 'warning' | 'critical';
}

interface MonitoringSchedule {
  id: string;
  engagement_id: string;
  name: string;
  frequency: string;
  cron_expression: string | null;
  enabled: boolean;
  sources: string[] | null;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  recent_runs: MonitoringRun[];
}

interface Props {
  engagementId: string;
  companyName: string;
}

function getAuthToken(): string | null {
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
        const raw = localStorage.getItem(key);
        if (raw) {
          const parsed = JSON.parse(raw) as { access_token?: string };
          return parsed.access_token ?? null;
        }
      }
    }
  } catch { /* ignore */ }
  return null;
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const SEVERITY_CONFIG = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', Icon: XCircle },
  warning: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', Icon: AlertTriangle },
  info: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', Icon: Activity },
};

const FREQ_LABELS: Record<string, string> = {
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  manual: 'Manual only',
};

function DeltaRow({ delta }: { delta: Delta }) {
  const cfg = SEVERITY_CONFIG[delta.severity] ?? SEVERITY_CONFIG.info;
  const isPositive = delta.delta_pct > 0;

  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${cfg.border} ${cfg.bg}`}>
      <cfg.Icon className={`w-3.5 h-3.5 flex-shrink-0 ${cfg.color}`} />
      <span className="text-[11px] text-theme-text flex-1 truncate">{delta.metric}</span>
      <div className="flex items-center gap-3 text-[10px] font-mono flex-shrink-0">
        <span className="text-theme-text-muted">{delta.baseline.toLocaleString()}</span>
        <span className="text-theme-text-muted">→</span>
        <span className={cfg.color}>{delta.current.toLocaleString()}</span>
        <span className={`flex items-center gap-0.5 font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {Math.abs(delta.delta_pct).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function RunCard({ run }: { run: MonitoringRun }) {
  const [open, setOpen] = useState(false);
  const deltas = run.deltas ?? [];
  const criticals = deltas.filter((d) => d.severity === 'critical');
  const warnings = deltas.filter((d) => d.severity === 'warning');

  return (
    <div className="border border-theme-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-theme-border/20 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          run.status === 'completed' ? 'bg-green-400' :
          run.status === 'running' ? 'bg-blue-400 animate-pulse' :
          run.status === 'failed' ? 'bg-red-400' : 'bg-theme-border'
        }`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold">
            {run.completed_at
              ? new Date(run.completed_at).toLocaleString('en-US', {
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                })
              : 'In progress'}
          </p>
          <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
            {deltas.length} metric{deltas.length !== 1 ? 's' : ''} checked
            {criticals.length > 0 && ` · ${criticals.length} critical`}
            {warnings.length > 0 && ` · ${warnings.length} warning`}
          </p>
        </div>
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
        }
      </button>
      {open && (
        <div className="px-4 py-3 border-t border-theme-border bg-theme-bg/40 space-y-1.5">
          {deltas.length === 0 ? (
            <p className="text-[11px] font-mono text-theme-text-muted text-center py-2">
              No deltas computed
            </p>
          ) : (
            deltas.map((d, i) => <DeltaRow key={i} delta={d} />)
          )}
          {run.error_message && (
            <p className="text-[11px] text-red-400 font-mono">{run.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}

function ScheduleCard({
  schedule,
  onToggle,
  onDelete,
  onRunNow,
}: {
  schedule: MonitoringSchedule;
  onToggle: (id: string, enabled: boolean) => void;
  onDelete: (id: string) => void;
  onRunNow: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [running, setRunning] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleRunNow = async () => {
    setRunning(true);
    await onRunNow(schedule.id);
    setRunning(false);
  };

  const handleDelete = async () => {
    setDeleting(true);
    await onDelete(schedule.id);
    setDeleting(false);
  };

  const recentRun = schedule.recent_runs[0] ?? null;

  return (
    <div className="border border-theme-border rounded-xl overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex-1 flex items-center gap-3 text-left min-w-0"
        >
          <div className="min-w-0">
            <p className="text-xs font-semibold truncate">{schedule.name}</p>
            <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
              {FREQ_LABELS[schedule.frequency] ?? schedule.frequency}
              {schedule.sources && schedule.sources.length > 0 && (
                ` · ${schedule.sources.slice(0, 3).join(', ')}${schedule.sources.length > 3 ? ` +${schedule.sources.length - 3}` : ''}`
              )}
              {recentRun?.completed_at && (
                ` · Last run ${new Date(recentRun.completed_at).toLocaleDateString()}`
              )}
            </p>
          </div>
          {expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
            : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
          }
        </button>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => onToggle(schedule.id, !schedule.enabled)}
            title={schedule.enabled ? 'Disable schedule' : 'Enable schedule'}
            className="text-theme-text-muted hover:text-theme-text transition-colors"
          >
            {schedule.enabled
              ? <ToggleRight className="w-4 h-4 text-green-400" />
              : <ToggleLeft className="w-4 h-4" />
            }
          </button>
          <button
            onClick={handleRunNow}
            disabled={running}
            title="Run now"
            className="p-1 rounded hover:bg-theme-border/30 text-theme-text-muted hover:text-theme-text transition-colors disabled:opacity-40"
          >
            {running
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Play className="w-3.5 h-3.5" />
            }
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            title="Delete schedule"
            className="p-1 rounded hover:bg-red-500/10 text-theme-text-muted hover:text-red-400 transition-colors disabled:opacity-40"
          >
            {deleting
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Trash2 className="w-3.5 h-3.5" />
            }
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-theme-border px-4 py-3 bg-theme-bg/40 space-y-2">
          {schedule.recent_runs.length === 0 ? (
            <p className="text-[11px] font-mono text-theme-text-muted text-center py-3">
              No runs yet — click ▶ to trigger the first run
            </p>
          ) : (
            schedule.recent_runs.map((run) => <RunCard key={run.id} run={run} />)
          )}
        </div>
      )}
    </div>
  );
}

function NewScheduleForm({
  engagementId,
  onCreated,
  onCancel,
}: {
  engagementId: string;
  onCreated: (s: MonitoringSchedule) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState('Monthly Portfolio Review');
  const [frequency, setFrequency] = useState('monthly');
  const [sources, setSources] = useState('salesforce, netsuite');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const resp = await fetch(`${API_BASE}/engagements/${engagementId}/monitoring`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          name,
          frequency,
          sources: sources.split(',').map((s) => s.trim()).filter(Boolean),
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `HTTP ${resp.status}`);
      }
      const created = await resp.json() as MonitoringSchedule;
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create schedule');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border border-theme-border rounded-xl p-4 space-y-3 bg-theme-bg/40">
      <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">New Monitoring Schedule</p>

      <div>
        <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-xs
                     focus:outline-none focus:border-theme-text-muted transition-colors"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Frequency</label>
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="w-full px-3 py-2 bg-theme-bg border border-theme-border rounded-lg text-xs
                       focus:outline-none focus:border-theme-text-muted transition-colors"
          >
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="manual">Manual only</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Sources</label>
          <input
            type="text"
            value={sources}
            onChange={(e) => setSources(e.target.value)}
            placeholder="salesforce, netsuite, hubspot"
            className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-xs
                       placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted transition-colors"
          />
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 font-mono">{error}</p>
      )}

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-[10px] font-mono text-theme-text-muted hover:text-theme-text transition-colors"
        >
          CANCEL
        </button>
        <button
          type="submit"
          disabled={loading || !name.trim()}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-theme-text text-theme-bg text-[10px] font-mono font-semibold
                     rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
          CREATE
        </button>
      </div>
    </form>
  );
}

export default function PortfolioPanel({ engagementId, companyName }: Props) {
  const [schedules, setSchedules] = useState<MonitoringSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const loadSchedules = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/engagements/${engagementId}/monitoring`, {
        headers: authHeaders(),
      });
      if (resp.ok) {
        setSchedules(await resp.json());
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [engagementId]);

  useEffect(() => { loadSchedules(); }, [loadSchedules]);

  const handleToggle = async (scheduleId: string, enabled: boolean) => {
    try {
      const resp = await fetch(`${API_BASE}/engagements/${engagementId}/monitoring/${scheduleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ enabled }),
      });
      if (resp.ok) {
        const updated = await resp.json() as MonitoringSchedule;
        setSchedules((prev) => prev.map((s) => (s.id === scheduleId ? updated : s)));
      }
    } catch { /* ignore */ }
  };

  const handleDelete = async (scheduleId: string) => {
    try {
      await fetch(`${API_BASE}/engagements/${engagementId}/monitoring/${scheduleId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setSchedules((prev) => prev.filter((s) => s.id !== scheduleId));
    } catch { /* ignore */ }
  };

  const handleRunNow = async (scheduleId: string) => {
    // For manual runs, we pass empty current_metrics — the backend will note no deltas
    // In production this would trigger a live source pull first
    try {
      const resp = await fetch(
        `${API_BASE}/engagements/${engagementId}/monitoring/${scheduleId}/run`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({ current_metrics: {} }),
        },
      );
      if (resp.ok) {
        // Refresh schedules to get updated run list
        await loadSchedules();
      }
    } catch { /* ignore */ }
  };

  const handleCreated = (schedule: MonitoringSchedule) => {
    setSchedules((prev) => [schedule, ...prev]);
    setShowForm(false);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Portfolio Monitoring</h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            Schedule recurring pulls from live sources to track {companyName} post-acquisition
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                     text-[10px] font-mono text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 transition-colors"
        >
          <Plus className="w-3 h-3" /> NEW SCHEDULE
        </button>
      </div>

      {showForm && (
        <NewScheduleForm
          engagementId={engagementId}
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-theme-text-muted" />
        </div>
      )}

      {!loading && schedules.length === 0 && !showForm && (
        <div className="border border-dashed border-theme-border rounded-xl p-10 text-center space-y-3">
          <Calendar className="w-7 h-7 text-theme-text-muted mx-auto" />
          <div>
            <p className="text-sm font-semibold">No monitoring schedules</p>
            <p className="text-xs text-theme-text-muted font-mono mt-1">
              Create a schedule to automatically track KPI changes vs acquisition baseline
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-theme-text text-theme-bg
                       text-xs font-mono font-semibold rounded-lg hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3.5 h-3.5" /> NEW SCHEDULE
          </button>
        </div>
      )}

      {!loading && schedules.length > 0 && (
        <div className="space-y-2">
          {schedules.map((s) => (
            <ScheduleCard
              key={s.id}
              schedule={s}
              onToggle={handleToggle}
              onDelete={handleDelete}
              onRunNow={handleRunNow}
            />
          ))}
        </div>
      )}

      {/* Info note */}
      {schedules.length > 0 && (
        <div className="border border-dashed border-theme-border rounded-xl px-4 py-3">
          <p className="text-[10px] font-mono text-theme-text-muted/70 text-center">
            Scheduled runs pull live data from configured sources and compute deltas vs the acquisition baseline snapshot
          </p>
        </div>
      )}
    </div>
  );
}
