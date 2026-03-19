import { useCallback, useEffect, useState } from 'react';
import {
  Scale, FileSearch, CheckCircle2, AlertTriangle, XCircle,
  Loader2, Trash2, ChevronDown, ChevronUp, RefreshCw,
} from 'lucide-react';
import { legalFindingsApi, type LegalFinding } from '../../lib/apiClient';

interface Props {
  engagementId: string;
  companyName: string;
}

const CLAUSE_LABELS: Record<string, string> = {
  change_of_control: 'Change of Control',
  ip_ownership:      'IP Ownership',
  non_compete:       'Non-Compete',
  litigation:        'Litigation',
  regulatory:        'Regulatory',
  other:             'Other',
};

const RISK_CONFIG: Record<string, { label: string; color: string; border: string; bg: string; Icon: React.ElementType }> = {
  critical: { label: 'CRITICAL', color: 'text-red-400',   border: 'border-red-500/30',   bg: 'bg-red-500/8',    Icon: XCircle },
  warning:  { label: 'WARNING',  color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/8',  Icon: AlertTriangle },
  info:     { label: 'INFO',     color: 'text-blue-400',  border: 'border-blue-500/30',  bg: 'bg-blue-500/8',   Icon: CheckCircle2 },
};

const CLAUSE_COLORS: Record<string, string> = {
  change_of_control: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
  ip_ownership:      'text-blue-400 border-blue-500/30 bg-blue-500/10',
  non_compete:       'text-orange-400 border-orange-500/30 bg-orange-500/10',
  litigation:        'text-red-400 border-red-500/30 bg-red-500/10',
  regulatory:        'text-amber-400 border-amber-500/30 bg-amber-500/10',
  other:             'text-theme-text-muted border-theme-border bg-theme-border/20',
};

export default function LegalDDPanel({ engagementId, companyName }: Props) {
  const [findings, setFindings]         = useState<LegalFinding[]>([]);
  const [loading, setLoading]           = useState(true);
  const [analyzing, setAnalyzing]       = useState(false);
  const [deletingId, setDeletingId]     = useState<string | null>(null);
  const [expandedId, setExpandedId]     = useState<string | null>(null);
  const [updatingId, setUpdatingId]     = useState<string | null>(null);
  const [clauseFilter, setClauseFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter]     = useState<string>('all');
  const [summary, setSummary]           = useState<{ total: number; critical: number; warning: number; info: number; unreviewed: number }>({
    total: 0, critical: 0, warning: 0, info: 0, unreviewed: 0,
  });

  const load = useCallback(async () => {
    try {
      const data = await legalFindingsApi.list(engagementId);
      setFindings(data);
      setSummary({
        total:      data.length,
        critical:   data.filter((f) => f.risk_level === 'critical').length,
        warning:    data.filter((f) => f.risk_level === 'warning').length,
        info:       data.filter((f) => f.risk_level === 'info').length,
        unreviewed: data.filter((f) => f.requires_review && !f.reviewed).length,
      });
    } catch {}
    setLoading(false);
  }, [engagementId]);

  useEffect(() => { load(); }, [load]);

  const handleAnalyzeAll = async () => {
    setAnalyzing(true);
    try {
      await legalFindingsApi.analyzeAll(engagementId);
      await load();
    } catch {}
    setAnalyzing(false);
  };

  const handleToggleReviewed = async (f: LegalFinding) => {
    setUpdatingId(f.id);
    try {
      const updated = await legalFindingsApi.update(engagementId, f.id, { reviewed: !f.reviewed });
      setFindings((prev) => prev.map((x) => (x.id === f.id ? updated : x)));
      setSummary((prev) => ({
        ...prev,
        unreviewed: prev.unreviewed + (f.reviewed ? 1 : -1),
      }));
    } catch {}
    setUpdatingId(null);
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await legalFindingsApi.delete(engagementId, id);
      setFindings((prev) => prev.filter((f) => f.id !== id));
      setSummary((prev) => {
        const removed = findings.find((f) => f.id === id);
        if (!removed) return prev;
        return {
          ...prev,
          total:      prev.total - 1,
          critical:   removed.risk_level === 'critical' ? prev.critical - 1 : prev.critical,
          warning:    removed.risk_level === 'warning'  ? prev.warning  - 1 : prev.warning,
          info:       removed.risk_level === 'info'     ? prev.info     - 1 : prev.info,
          unreviewed: removed.requires_review && !removed.reviewed ? prev.unreviewed - 1 : prev.unreviewed,
        };
      });
    } catch {}
    setDeletingId(null);
  };

  const filtered = findings.filter((f) => {
    if (clauseFilter !== 'all' && f.clause_type !== clauseFilter) return false;
    if (riskFilter !== 'all'   && f.risk_level   !== riskFilter)   return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-5 h-5 animate-spin text-theme-text-muted" />
        <span className="ml-2 text-sm font-mono text-theme-text-muted">Loading…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Scale className="w-4 h-4 text-purple-400" />
            Legal Due Diligence
          </h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            Contract clause scanner · {companyName}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                       text-[10px] font-mono text-theme-text-muted hover:text-theme-text
                       hover:bg-theme-border/30 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            REFRESH
          </button>
          <button
            onClick={handleAnalyzeAll}
            disabled={analyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 border border-purple-500/30
                       text-purple-400 text-[10px] font-mono rounded-lg hover:bg-purple-500/20
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {analyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileSearch className="w-3 h-3" />}
            {analyzing ? 'ANALYZING…' : 'ANALYZE ALL DOCUMENTS'}
          </button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {[
          { label: 'TOTAL',      value: summary.total,      color: 'text-theme-text' },
          { label: 'CRITICAL',   value: summary.critical,   color: 'text-red-400' },
          { label: 'WARNING',    value: summary.warning,    color: 'text-amber-400' },
          { label: 'INFO',       value: summary.info,       color: 'text-blue-400' },
          { label: 'UNREVIEWED', value: summary.unreviewed, color: 'text-orange-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="border border-theme-border rounded-xl px-3 py-3 text-center">
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-[9px] font-mono text-theme-text-muted mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      {findings.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono text-theme-text-muted">FILTER:</span>

          {/* Clause type filter */}
          <div className="flex items-center gap-1">
            {['all', ...Object.keys(CLAUSE_LABELS)].map((type) => (
              <button
                key={type}
                onClick={() => setClauseFilter(type)}
                className={`px-2 py-0.5 text-[9px] font-mono rounded-md transition-colors border ${
                  clauseFilter === type
                    ? 'bg-theme-text text-theme-bg border-theme-text font-semibold'
                    : 'border-theme-border text-theme-text-muted hover:text-theme-text'
                }`}
              >
                {type === 'all' ? 'ALL CLAUSES' : CLAUSE_LABELS[type].toUpperCase()}
              </button>
            ))}
          </div>

          <div className="w-px h-4 bg-theme-border" />

          {/* Risk filter */}
          <div className="flex items-center gap-1">
            {['all', 'critical', 'warning', 'info'].map((risk) => (
              <button
                key={risk}
                onClick={() => setRiskFilter(risk)}
                className={`px-2 py-0.5 text-[9px] font-mono rounded-md transition-colors border ${
                  riskFilter === risk
                    ? 'bg-theme-text text-theme-bg border-theme-text font-semibold'
                    : 'border-theme-border text-theme-text-muted hover:text-theme-text'
                }`}
              >
                {risk === 'all' ? 'ALL RISK' : risk.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Findings list */}
      {filtered.length === 0 ? (
        <div className="border border-dashed border-theme-border rounded-xl p-10 text-center">
          <Scale className="w-6 h-6 text-theme-text-muted mx-auto mb-2 opacity-50" />
          <p className="text-xs font-mono text-theme-text-muted">
            {findings.length === 0
              ? 'No findings yet — upload contracts and click Analyze All Documents'
              : 'No findings match the current filters'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((f) => {
            const rc  = RISK_CONFIG[f.risk_level] ?? RISK_CONFIG.info;
            const cc  = CLAUSE_COLORS[f.clause_type] ?? CLAUSE_COLORS.other;
            const isExpanded = expandedId === f.id;

            return (
              <div
                key={f.id}
                className={`border rounded-xl px-4 py-3 ${rc.border} ${rc.bg} transition-all`}
              >
                {/* Top row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <rc.Icon className={`w-3.5 h-3.5 ${rc.color} flex-shrink-0`} />
                    <span className={`text-[9px] font-mono font-semibold ${rc.color}`}>{rc.label}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${cc}`}>
                      {CLAUSE_LABELS[f.clause_type] ?? f.clause_type}
                    </span>
                    {f.reviewed && (
                      <span className="text-[9px] font-mono text-green-400 border border-green-500/30 bg-green-500/10 px-1.5 py-0.5 rounded">
                        REVIEWED
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    {/* Mark reviewed */}
                    <button
                      onClick={() => handleToggleReviewed(f)}
                      disabled={updatingId === f.id}
                      title={f.reviewed ? 'Mark as unreviewed' : 'Mark as reviewed'}
                      className={`p-1.5 rounded-lg transition-colors ${
                        f.reviewed
                          ? 'text-green-400 hover:text-theme-text-muted hover:bg-theme-border/30'
                          : 'text-theme-text-muted hover:text-green-400 hover:bg-green-500/10'
                      }`}
                    >
                      {updatingId === f.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <CheckCircle2 className="w-3.5 h-3.5" />
                      }
                    </button>

                    {/* Expand/collapse */}
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : f.id)}
                      className="p-1.5 text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 rounded-lg transition-colors"
                    >
                      {isExpanded
                        ? <ChevronUp className="w-3.5 h-3.5" />
                        : <ChevronDown className="w-3.5 h-3.5" />
                      }
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(f.id)}
                      disabled={deletingId === f.id}
                      className="p-1.5 text-theme-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      {deletingId === f.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />
                      }
                    </button>
                  </div>
                </div>

                {/* Excerpt preview */}
                <p className={`text-[11px] font-mono text-theme-text-muted mt-2 ${isExpanded ? '' : 'line-clamp-2'}`}>
                  "{f.text_excerpt}"
                </p>

                {/* Expanded: notes + metadata */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-theme-border/40 space-y-2">
                    {f.notes && (
                      <div>
                        <p className="text-[9px] font-mono text-theme-text-muted uppercase mb-1">Notes</p>
                        <p className="text-[11px] font-mono text-theme-text">{f.notes}</p>
                      </div>
                    )}
                    <p className="text-[9px] font-mono text-theme-text-muted">
                      {f.requires_review ? 'Requires human review' : 'No review required'} ·{' '}
                      {new Date(f.created_at).toLocaleDateString()}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
