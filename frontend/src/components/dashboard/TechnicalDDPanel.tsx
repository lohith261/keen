import { useState, useEffect, useCallback, useRef } from 'react';
import { BarChart2, Loader2, Trash2, GitBranch, Users, Zap, AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';
import { technicalDDApi, type TechnicalDDReport } from '../../lib/apiClient';

interface Props {
  engagementId: string;
  companyName: string;
  readOnly?: boolean;
}

function HealthDial({ score }: { score: number }) {
  const color = score >= 70 ? 'text-green-400' : score >= 40 ? 'text-amber-400' : 'text-red-400';
  const bgColor = score >= 70 ? 'stroke-green-400' : score >= 40 ? 'stroke-amber-400' : 'stroke-red-400';
  const circumference = 2 * Math.PI * 36;
  const dash = (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center w-24 h-24">
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="36" fill="none" stroke="currentColor" strokeWidth="6" className="text-theme-border" />
        <circle
          cx="40" cy="40" r="36" fill="none" strokeWidth="6"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          className={bgColor}
        />
      </svg>
      <div className="text-center z-10">
        <span className={`text-xl font-bold font-mono ${color}`}>{score}</span>
        <span className="block text-[9px] font-mono text-theme-text-muted">/ 100</span>
      </div>
    </div>
  );
}

function LangBar({ langStats }: { langStats: Record<string, number> }) {
  const total = Object.values(langStats).reduce((s, v) => s + v, 0);
  if (total === 0) return null;
  const colors = ['bg-blue-400', 'bg-green-400', 'bg-amber-400', 'bg-purple-400', 'bg-red-400', 'bg-cyan-400'];
  const entries = Object.entries(langStats).sort((a, b) => b[1] - a[1]).slice(0, 6);

  return (
    <div className="space-y-1.5">
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        {entries.map(([lang, bytes], i) => (
          <div
            key={lang}
            className={`${colors[i % colors.length]} rounded-full`}
            style={{ width: `${(bytes / total) * 100}%` }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        {entries.map(([lang, bytes], i) => (
          <div key={lang} className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-full ${colors[i % colors.length]}`} />
            <span className="text-[10px] font-mono text-theme-text-muted">
              {lang} {Math.round((bytes / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TechnicalDDPanel({ engagementId, companyName: _companyName, readOnly = false }: Props) {
  const [reports, setReports]     = useState<TechnicalDDReport[]>([]);
  const [loading, setLoading]     = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [repoUrl, setRepoUrl]     = useState('');
  const [token, setToken]         = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await technicalDDApi.list(engagementId);
      setReports(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, [engagementId]);

  useEffect(() => { load(); }, [load]);

  // Poll while any report is pending
  useEffect(() => {
    const hasPending = reports.some((r) => r.status === 'pending');
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const fresh = await technicalDDApi.list(engagementId);
          setReports(fresh);
          if (!fresh.some((r) => r.status === 'pending')) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
          }
        } catch { /* ignore */ }
      }, 5000);
    }
    return () => {
      if (!hasPending && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [engagementId, reports]);

  const handleAnalyze = async () => {
    if (!repoUrl.trim()) return;
    setAnalyzing(true);
    try {
      const report = await technicalDDApi.create(engagementId, repoUrl.trim(), token.trim() || undefined);
      setReports((prev) => [report, ...prev]);
      setRepoUrl('');
      setToken('');
    } catch { /* ignore */ }
    setAnalyzing(false);
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await technicalDDApi.delete(engagementId, id);
      setReports((prev) => prev.filter((r) => r.id !== id));
    } catch { /* ignore */ }
    setDeletingId(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-theme-text-muted text-xs font-mono">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-purple-400" />
          Technical Due Diligence
        </h3>
        <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
          GitHub repo analysis · health score · bus factor · security
        </p>
      </div>

      {/* Analyze form */}
      {!readOnly && (
        <div className="border border-theme-border rounded-xl p-4 space-y-3 bg-theme-surface/30">
          <p className="text-[11px] font-mono font-semibold text-theme-text">Analyze a GitHub repository</p>
          <div className="flex gap-3">
            <input
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="flex-1 bg-transparent border border-theme-border rounded-lg px-3 py-1.5
                         text-xs font-mono placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted"
            />
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="GitHub token (optional)"
              type="password"
              className="w-48 bg-transparent border border-theme-border rounded-lg px-3 py-1.5
                         text-xs font-mono placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted"
            />
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !repoUrl.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-theme-text text-theme-bg
                         text-[10px] font-mono font-semibold rounded-lg hover:opacity-90
                         transition-opacity disabled:opacity-40 flex-shrink-0"
            >
              {analyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <GitBranch className="w-3 h-3" />}
              ANALYZE
            </button>
          </div>
        </div>
      )}

      {/* Reports list */}
      {reports.length === 0 ? (
        <div className="border border-dashed border-theme-border rounded-xl p-10 text-center">
          <GitBranch className="w-6 h-6 text-theme-text-muted mx-auto mb-2" />
          <p className="text-xs font-mono text-theme-text-muted">No repositories analyzed yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => (
            <div key={r.id} className="border border-theme-border rounded-xl p-4 space-y-4">
              {/* Repo header */}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <GitBranch className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
                    <a
                      href={r.repo_url ?? '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-mono font-semibold text-blue-400 hover:underline truncate"
                    >
                      {r.repo_url ?? 'Unknown repo'}
                    </a>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border flex-shrink-0 ${
                      r.status === 'completed' ? 'border-green-500/40 text-green-400 bg-green-500/10' :
                      r.status === 'pending'   ? 'border-blue-500/40 text-blue-400 bg-blue-500/10'  :
                      r.status === 'failed'    ? 'border-red-500/40 text-red-400 bg-red-500/10'     :
                      'border-theme-border text-theme-text-muted'
                    }`}>
                      {r.status === 'pending' && <RefreshCw className="w-2 h-2 inline animate-spin mr-0.5" />}
                      {r.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-theme-text-muted mt-1">
                    {new Date(r.created_at).toLocaleString()}
                  </p>
                </div>
                {!readOnly && (
                  <button
                    onClick={() => handleDelete(r.id)}
                    disabled={deletingId === r.id}
                    className="p-1.5 text-theme-text-muted hover:text-red-400 hover:bg-red-500/10 rounded transition-colors flex-shrink-0"
                  >
                    {deletingId === r.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                  </button>
                )}
              </div>

              {r.status === 'pending' && (
                <div className="flex items-center gap-2 text-xs font-mono text-blue-400">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analysis in progress…
                </div>
              )}

              {r.status === 'failed' && (
                <div className="flex items-center gap-2 text-xs font-mono text-red-400">
                  <AlertCircle className="w-3.5 h-3.5" /> {r.error_message ?? 'Analysis failed'}
                </div>
              )}

              {r.status === 'completed' && (
                <>
                  {/* Health score + metrics */}
                  <div className="flex items-center gap-6 flex-wrap">
                    {r.health_score !== null && (
                      <HealthDial score={r.health_score} />
                    )}
                    <div className="grid grid-cols-2 gap-3 flex-1 min-w-0">
                      <div className="border border-theme-border rounded-lg p-3">
                        <div className="flex items-center gap-1.5 text-theme-text-muted mb-1">
                          <Users className="w-3 h-3" />
                          <span className="text-[10px] font-mono">BUS FACTOR</span>
                        </div>
                        <p className={`text-xl font-bold font-mono ${
                          (r.bus_factor ?? 0) <= 1 ? 'text-red-400' :
                          (r.bus_factor ?? 0) <= 2 ? 'text-amber-400' : 'text-green-400'
                        }`}>
                          {r.bus_factor ?? '—'}
                        </p>
                        <p className="text-[9px] font-mono text-theme-text-muted mt-0.5">
                          {(r.bus_factor ?? 0) <= 1 ? 'Critical risk' :
                           (r.bus_factor ?? 0) <= 2 ? 'Moderate risk' : 'Healthy'}
                        </p>
                      </div>
                      <div className="border border-theme-border rounded-lg p-3">
                        <div className="flex items-center gap-1.5 text-theme-text-muted mb-1">
                          <Users className="w-3 h-3" />
                          <span className="text-[10px] font-mono">CONTRIBUTORS</span>
                        </div>
                        <p className="text-xl font-bold font-mono text-theme-text">
                          {r.contributor_count ?? '—'}
                        </p>
                      </div>
                      <div className="border border-theme-border rounded-lg p-3">
                        <div className="flex items-center gap-1.5 text-theme-text-muted mb-1">
                          <Zap className="w-3 h-3" />
                          <span className="text-[10px] font-mono">COMMITS/WEEK</span>
                        </div>
                        <p className="text-xl font-bold font-mono text-theme-text">
                          {r.commit_velocity !== null ? r.commit_velocity.toFixed(1) : '—'}
                        </p>
                      </div>
                      <div className="border border-theme-border rounded-lg p-3">
                        <div className="flex items-center gap-1.5 text-theme-text-muted mb-1">
                          <AlertCircle className="w-3 h-3" />
                          <span className="text-[10px] font-mono">OPEN ISSUES</span>
                        </div>
                        <p className="text-xl font-bold font-mono text-theme-text">
                          {r.open_issues_count ?? '—'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Language breakdown */}
                  {r.language_stats && Object.keys(r.language_stats).length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-theme-text-muted mb-2">LANGUAGES</p>
                      <LangBar langStats={r.language_stats} />
                    </div>
                  )}

                  {/* Security vulns */}
                  {r.security_vulnerabilities && (r.security_vulnerabilities as unknown[]).length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-theme-text-muted mb-1.5 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-red-400" /> SECURITY VULNERABILITIES
                      </p>
                      <div className="space-y-1">
                        {(r.security_vulnerabilities as Record<string, string>[]).map((v, i) => (
                          <div key={i} className="text-[11px] font-mono text-red-400 border border-red-500/20 rounded px-2 py-1">
                            {v.severity?.toUpperCase()} — {v.description ?? JSON.stringify(v)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dep risks */}
                  {r.dependency_risks && (r.dependency_risks as unknown[]).length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-theme-text-muted mb-1.5 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-amber-400" /> DEPENDENCY RISKS
                      </p>
                      <div className="space-y-1">
                        {(r.dependency_risks as Record<string, string>[]).map((d, i) => (
                          <div key={i} className="text-[11px] font-mono text-amber-400 border border-amber-500/20 rounded px-2 py-1">
                            {d.name ?? JSON.stringify(d)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
