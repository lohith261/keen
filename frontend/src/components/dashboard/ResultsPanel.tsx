import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  AlertTriangle, XCircle, Info, ChevronDown, ChevronRight,
  Loader2, RefreshCw, Eye, EyeOff, FileText, TrendingUp, Download,
  FileSpreadsheet, HardDrive, LayoutList, ClipboardList,
} from 'lucide-react';
import type { Engagement, Finding } from '../../lib/apiClient';
import { findingsApi } from '../../lib/apiClient';
import { useToast } from '../ui/Toast';

/** Safely coerce any value to a renderable string. */
function toStr(val: unknown): string {
  if (val == null) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  if (Array.isArray(val)) return val.map(toStr).join(', ');
  if (typeof val === 'object') {
    const v = val as Record<string, unknown>;
    // Try common text fields before falling back to JSON
    return (
      (v.title as string) ?? (v.description as string) ?? (v.text as string) ?? JSON.stringify(val)
    );
  }
  return String(val);
}

/** Lightweight styled wrapper for inline markdown in findings. */
function Prose({ children }: { children: unknown }) {
  const text = toStr(children);
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="text-[11px] text-theme-text leading-relaxed mb-1 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-theme-text">{children}</strong>,
        em: ({ children }) => <em className="italic text-theme-text-muted">{children}</em>,
        ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 my-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside space-y-0.5 my-1">{children}</ol>,
        li: ({ children }) => <li className="text-[11px] text-theme-text leading-relaxed">{children}</li>,
        h3: ({ children }) => <h3 className="text-[11px] font-semibold text-theme-text mt-2 mb-0.5">{children}</h3>,
        h4: ({ children }) => <h4 className="text-[11px] font-medium text-theme-text-muted mt-1.5 mb-0.5">{children}</h4>,
        code: ({ children }) => <code className="text-[10px] font-mono bg-theme-border/40 px-1 rounded">{children}</code>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-theme-border pl-2 my-1 text-theme-text-muted">{children}</blockquote>,
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

const BACKEND_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

interface Props {
  engagement: Engagement;
}

const SEVERITY_CONFIG = {
  critical: {
    icon: XCircle,
    color: 'text-red-400',
    border: 'border-red-500/30',
    bg: 'bg-red-500/8',
    badge: 'bg-red-500/15 border-red-500/30 text-red-400',
    label: 'CRITICAL',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-400',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/8',
    badge: 'bg-amber-500/15 border-amber-500/30 text-amber-400',
    label: 'WARNING',
  },
  info: {
    icon: Info,
    color: 'text-blue-400',
    border: 'border-blue-500/30',
    bg: 'bg-blue-500/8',
    badge: 'bg-blue-500/15 border-blue-500/30 text-blue-400',
    label: 'INFO',
  },
} as const;

type SevKey = keyof typeof SEVERITY_CONFIG;

const REC_CONFIG: Record<string, { color: string; border: string; bg: string; label: string }> = {
  proceed: { color: 'text-green-400', border: 'border-green-500/40', bg: 'bg-green-500/10', label: 'PROCEED' },
  proceed_with_caution: { color: 'text-amber-400', border: 'border-amber-500/40', bg: 'bg-amber-500/10', label: 'PROCEED WITH CAUTION' },
  caution: { color: 'text-amber-400', border: 'border-amber-500/40', bg: 'bg-amber-500/10', label: 'CAUTION' },
  do_not_proceed: { color: 'text-red-400', border: 'border-red-500/40', bg: 'bg-red-500/10', label: 'DO NOT PROCEED' },
  reject: { color: 'text-red-400', border: 'border-red-500/40', bg: 'bg-red-500/10', label: 'REJECT' },
};

function ExecutiveSummaryCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(true);
  const data = (finding.data ?? {}) as Record<string, unknown>;
  const rec = (data.recommendation as string) ?? '';
  const recCfg = REC_CONFIG[rec] ?? REC_CONFIG['proceed_with_caution'];
  const keyFindings = ((data.key_findings as unknown[]) ?? []).map(toStr);
  const riskAssessment = toStr(data.risk_assessment ?? '');
  const rationale = toStr(data.rationale ?? finding.description ?? '');
  const reportSections = (data.report_sections as number) ?? 0;

  return (
    <div className={`border ${recCfg.border} rounded-xl overflow-hidden`}>
      <button
        onClick={() => setExpanded((v) => !v)}
        className={`w-full flex items-start gap-3 px-5 py-4 text-left hover:bg-theme-border/20 transition-colors ${recCfg.bg}`}
      >
        <FileText className={`w-4 h-4 ${recCfg.color} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold leading-snug">Executive Summary — GPT-4o Analysis</p>
          <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
            Generated by OpenAI GPT-4o · {reportSections} report sections
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded border ${recCfg.bg} ${recCfg.border} ${recCfg.color}`}>
            {recCfg.label}
          </span>
          {expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted" />
            : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted" />
          }
        </div>
      </button>

      {expanded && (
        <div className="px-5 py-4 border-t border-theme-border bg-theme-bg/40 space-y-4">
          {riskAssessment && (
            <div>
              <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1">Risk Assessment</p>
              <Prose>{riskAssessment}</Prose>
            </div>
          )}

          {keyFindings.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-2">Key Findings</p>
              <ul className="space-y-1.5">
                {keyFindings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <TrendingUp className="w-3 h-3 text-theme-text-muted flex-shrink-0 mt-0.5" />
                    <span className="text-[11px] text-theme-text leading-relaxed">{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {rationale && (
            <div>
              <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1">Recommendation Rationale</p>
              <Prose>{rationale}</Prose>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Browser-sourced systems that should show a TinyFish attribution badge
const TINYFISH_SYSTEMS = new Set([
  'bloomberg', 'capiq', 'pitchbook', 'sales_navigator',
  'quickbooks', 'zoominfo', 'marketo', 'dynamics', 'sap', 'oracle',
]);

// Human-readable source names
const SOURCE_LABELS: Record<string, string> = {
  sales_navigator: 'LinkedIn Sales Navigator',
  sec_edgar: 'SEC EDGAR',
  bloomberg: 'Bloomberg Terminal',
  capiq: 'Capital IQ',
  pitchbook: 'PitchBook',
  zoominfo: 'ZoomInfo',
  salesforce_vs_dynamics: 'Salesforce ↔ Dynamics',
  salesforce_vs_netsuite: 'Salesforce ↔ NetSuite',
  sap_vs_oracle: 'SAP ↔ Oracle',
  sap_vs_netsuite: 'SAP ↔ NetSuite',
};

function getSourceLabel(raw: string): string {
  const lower = raw.toLowerCase().replace(/\s+/g, '_');
  return SOURCE_LABELS[lower] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function FindingCard({ finding, autoExpand = false }: { finding: Finding; autoExpand?: boolean }) {
  const [expanded, setExpanded] = useState(autoExpand);
  const sev = (finding.severity as SevKey) in SEVERITY_CONFIG
    ? (finding.severity as SevKey)
    : 'info';
  const cfg = SEVERITY_CONFIG[sev];
  const Icon = cfg.icon;
  const src = (finding.source_system ?? '').toLowerCase();
  const isTinyFish = TINYFISH_SYSTEMS.has(src);

  return (
    <div className={`border ${cfg.border} rounded-xl overflow-hidden`}>
      <button
        onClick={() => setExpanded((v) => !v)}
        className={`w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-theme-border/20 transition-colors ${cfg.bg}`}
      >
        <Icon className={`w-4 h-4 ${cfg.color} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold leading-snug">{finding.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {finding.source_system && (
              <span className="text-[10px] font-mono text-theme-text-muted">
                {getSourceLabel(finding.source_system)}
              </span>
            )}
            {isTinyFish && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan-500/30 text-cyan-400 bg-cyan-500/8">
                🐟 TinyFish
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {finding.requires_human_review && (
            <span className="hidden sm:inline text-[9px] font-mono px-1.5 py-0.5 rounded border border-amber-500/30 text-amber-400 bg-amber-500/10">
              REVIEW
            </span>
          )}
          {expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted" />
            : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted" />
          }
        </div>
      </button>

      {expanded && finding.description && (
        <div className="px-4 py-3 border-t border-theme-border bg-theme-bg/40 space-y-2">
          <Prose>{finding.description}</Prose>
          <div className="flex flex-wrap gap-2 pt-1">
            <span className={`inline-flex items-center gap-1 text-[9px] font-mono px-2 py-0.5 rounded-full border ${cfg.badge}`}>
              <Icon className="w-2.5 h-2.5" /> {cfg.label}
            </span>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded-full border border-theme-border text-theme-text-muted">
              {finding.finding_type.replace(/_/g, ' ').toUpperCase()}
            </span>
            {isTinyFish && (
              <span className="text-[9px] font-mono px-2 py-0.5 rounded-full border border-cyan-500/30 text-cyan-400">
                🐟 via TinyFish browser automation
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SeverityGroup({
  severity,
  findings,
  defaultOpen = false,
  autoExpandCards = false,
}: {
  severity: SevKey;
  findings: Finding[];
  defaultOpen?: boolean;
  autoExpandCards?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (findings.length === 0) return null;
  const cfg = SEVERITY_CONFIG[severity];
  const Icon = cfg.icon;

  return (
    <div className="border border-theme-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-theme-bg/60 hover:bg-theme-border/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className={`w-4 h-4 ${cfg.color}`} />
          <span className="text-xs font-semibold tracking-wide">{cfg.label}</span>
          <span className={`px-2 py-0.5 rounded-full border text-[10px] font-mono font-semibold ${cfg.badge}`}>
            {findings.length}
          </span>
        </div>
        {open
          ? <ChevronDown className="w-4 h-4 text-theme-text-muted" />
          : <ChevronRight className="w-4 h-4 text-theme-text-muted" />
        }
      </button>
      {open && (
        <div className="px-4 py-3 space-y-2 border-t border-theme-border bg-theme-bg/20">
          {findings.map((f) => (
            <FindingCard key={f.id} finding={f} autoExpand={autoExpandCards} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Deal Brief ────────────────────────────────────────────────────────────────
function DealBrief({
  engagement,
  findings,
}: {
  engagement: Engagement;
  findings: Finding[];
}) {
  const execSummary = findings.find((f) => f.finding_type === 'executive_summary');
  const regular = findings.filter((f) => f.finding_type !== 'executive_summary');
  const criticals = regular.filter((f) => f.severity === 'critical');
  const warnings  = regular.filter((f) => f.severity === 'warning');
  const infos     = regular.filter((f) => f.severity === 'info');

  const data = (execSummary?.data ?? {}) as Record<string, unknown>;
  const rec = toStr(data.recommendation ?? '');
  const rationale = toStr(data.rationale ?? execSummary?.description ?? '');
  const keyFindings = ((data.key_findings as unknown[]) ?? []).map(toStr);
  const recCfg = REC_CONFIG[rec] ?? REC_CONFIG['proceed_with_caution'];

  const topCriticals = criticals.slice(0, 5);
  const topWarnings  = warnings.slice(0, 3);

  return (
    <div className="space-y-4 print:text-black">
      {/* Header */}
      <div className="border border-theme-border rounded-xl px-5 py-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-widest mb-1">Deal Brief</p>
          <h2 className="text-base font-bold leading-tight">{engagement.company_name}</h2>
          {engagement.pe_firm && (
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">{engagement.pe_firm}</p>
          )}
          {engagement.deal_size && (
            <p className="text-[11px] font-mono text-theme-text-muted">{engagement.deal_size}</p>
          )}
          <p className="text-[10px] font-mono text-theme-text-muted/60 mt-1">
            {engagement.completed_at
              ? `Analysis completed ${new Date(engagement.completed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
              : 'KEEN Due Diligence Platform'}
            {' · '}{regular.length} findings
          </p>
        </div>
        {execSummary && (
          <div className={`flex-shrink-0 px-3 py-2 rounded-lg border text-center ${recCfg.bg} ${recCfg.border}`}>
            <p className="text-[9px] font-mono text-theme-text-muted mb-1">RECOMMENDATION</p>
            <p className={`text-xs font-bold ${recCfg.color}`}>{recCfg.label}</p>
          </div>
        )}
      </div>

      {/* Severity summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="border border-red-500/30 bg-red-500/8 rounded-xl px-4 py-3 text-center">
          <p className="text-2xl font-bold text-red-400">{criticals.length}</p>
          <p className="text-[10px] font-mono text-red-400/70 mt-0.5">CRITICAL</p>
        </div>
        <div className="border border-amber-500/30 bg-amber-500/8 rounded-xl px-4 py-3 text-center">
          <p className="text-2xl font-bold text-amber-400">{warnings.length}</p>
          <p className="text-[10px] font-mono text-amber-400/70 mt-0.5">WARNING</p>
        </div>
        <div className="border border-blue-500/30 bg-blue-500/8 rounded-xl px-4 py-3 text-center">
          <p className="text-2xl font-bold text-blue-400">{infos.length}</p>
          <p className="text-[10px] font-mono text-blue-400/70 mt-0.5">INFO</p>
        </div>
      </div>

      {/* Rationale */}
      {rationale && (
        <div className="border border-theme-border rounded-xl px-5 py-4 space-y-2">
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">Executive Rationale</p>
          <Prose>{rationale}</Prose>
        </div>
      )}

      {/* Key findings from exec summary */}
      {keyFindings.length > 0 && (
        <div className="border border-theme-border rounded-xl px-5 py-4 space-y-2">
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-2">Key Findings</p>
          <ul className="space-y-1.5">
            {keyFindings.map((f, i) => (
              <li key={i} className="flex items-start gap-2">
                <TrendingUp className="w-3 h-3 text-theme-text-muted flex-shrink-0 mt-0.5" />
                <span className="text-[11px] text-theme-text leading-relaxed">{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Top criticals */}
      {topCriticals.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider px-1">
            Critical Issues ({criticals.length})
          </p>
          {topCriticals.map((f) => (
            <div key={f.id} className="border border-red-500/30 bg-red-500/8 rounded-xl px-4 py-3 flex items-start gap-3">
              <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-theme-text leading-snug">{f.title}</p>
                {f.source_system && (
                  <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
                    {f.source_system.replace(/_/g, ' → ').toUpperCase()}
                  </p>
                )}
              </div>
            </div>
          ))}
          {criticals.length > 5 && (
            <p className="text-[10px] font-mono text-theme-text-muted/60 px-1">
              +{criticals.length - 5} more critical issues — see full findings
            </p>
          )}
        </div>
      )}

      {/* Top warnings */}
      {topWarnings.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider px-1">
            Key Warnings ({warnings.length})
          </p>
          {topWarnings.map((f) => (
            <div key={f.id} className="border border-amber-500/30 bg-amber-500/8 rounded-xl px-4 py-3 flex items-start gap-3">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-theme-text leading-snug">{f.title}</p>
                {f.source_system && (
                  <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
                    {f.source_system.replace(/_/g, ' → ').toUpperCase()}
                  </p>
                )}
              </div>
            </div>
          ))}
          {warnings.length > 3 && (
            <p className="text-[10px] font-mono text-theme-text-muted/60 px-1">
              +{warnings.length - 3} more warnings — see full findings
            </p>
          )}
        </div>
      )}

      {/* Footer note */}
      <div className="border border-dashed border-theme-border rounded-xl px-4 py-3">
        <p className="text-[10px] font-mono text-theme-text-muted/60 text-center">
          Generated by KEEN · AI-assisted due diligence · For internal use only
        </p>
      </div>
    </div>
  );
}

// ─── Main Results Panel ────────────────────────────────────────────────────────
export default function ResultsPanel({ engagement }: Props) {
  const { addToast } = useToast();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReviewOnly, setShowReviewOnly] = useState(false);
  const [briefView, setBriefView] = useState(false);
  const [sheetsLoading, setSheetsLoading] = useState(false);
  const [sheetsError, setSheetsError] = useState<string | null>(null);
  const [driveLoading, setDriveLoading] = useState(false);
  const [driveError, setDriveError] = useState<string | null>(null);

  const fetchFindings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await findingsApi.list(engagement.id);
      setFindings(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load findings');
    } finally {
      setLoading(false);
    }
  };

  const handleSheetsExport = async () => {
    setSheetsLoading(true);
    setSheetsError(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/v1/engagements/${engagement.id}/export/gsheets?credentials_id=${engagement.id}`,
        { headers: { 'Content-Type': 'application/json' } },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`);
      }
      const { url } = await res.json() as { url: string };
      addToast({
        type: 'success',
        message: 'Google Sheet created',
        detail: 'Report exported successfully',
        action: { label: 'Open Sheet', onClick: () => window.open(url, '_blank', 'noopener,noreferrer') },
        duration: 10000,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Google Sheets export failed';
      setSheetsError(msg);
      addToast({ type: 'error', message: 'Sheets export failed', detail: msg });
    } finally {
      setSheetsLoading(false);
    }
  };

  const handleDriveExport = async () => {
    setDriveLoading(true);
    setDriveError(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/v1/engagements/${engagement.id}/export/drive?credentials_id=${engagement.id}`,
        { headers: { 'Content-Type': 'application/json' } },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`);
      }
      const data = await res.json() as {
        status: string;
        pdf?: { url: string };
        excel?: { url: string };
      };
      const pdfUrl  = data.pdf?.url;
      const xlsxUrl = data.excel?.url;
      addToast({
        type: 'success',
        message: 'Uploaded to Google Drive',
        detail: [pdfUrl && 'PDF', xlsxUrl && 'Excel'].filter(Boolean).join(' + ') + ' ready',
        action: pdfUrl
          ? { label: 'Open PDF', onClick: () => window.open(pdfUrl, '_blank', 'noopener,noreferrer') }
          : xlsxUrl
          ? { label: 'Open Excel', onClick: () => window.open(xlsxUrl, '_blank', 'noopener,noreferrer') }
          : undefined,
        duration: 12000,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Google Drive export failed';
      setDriveError(msg);
      addToast({ type: 'error', message: 'Drive upload failed', detail: msg });
    } finally {
      setDriveLoading(false);
    }
  };

  // Re-fetch whenever the engagement id changes OR the pipeline transitions to
  // completed — this ensures findings that were committed at the end of the
  // orchestrator run are picked up without the user having to manually refresh.
  useEffect(() => {
    fetchFindings();
  }, [engagement.id, engagement.status]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-theme-text-muted" />
        <p className="text-xs font-mono text-theme-text-muted">Loading findings…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <XCircle className="w-8 h-8 text-red-400" />
        <p className="text-sm font-semibold">Failed to load findings</p>
        <p className="text-xs text-theme-text-muted font-mono">{error}</p>
        <button
          onClick={fetchFindings}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono border border-theme-border rounded-lg hover:bg-theme-border/30 transition-colors"
        >
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    );
  }

  // Separate executive summary from regular findings
  const execSummaryFinding = findings.find((f) => f.finding_type === 'executive_summary');
  const regularFindings = findings.filter((f) => f.finding_type !== 'executive_summary');

  const visible = showReviewOnly ? regularFindings.filter((f) => f.requires_human_review) : regularFindings;
  const criticals = visible.filter((f) => f.severity === 'critical');
  const warnings  = visible.filter((f) => f.severity === 'warning');
  const infos     = visible.filter((f) => f.severity === 'info');
  const reviewCount = regularFindings.filter((f) => f.requires_human_review).length;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="border border-theme-border rounded-xl p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-widest mb-1">Due Diligence Findings</p>
            <h3 className="text-base font-bold">{engagement.company_name}</h3>
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
              {engagement.completed_at
                ? `Completed ${new Date(engagement.completed_at).toLocaleString()}`
                : 'Pipeline complete'}
              {' · '}<span className="font-semibold text-theme-text">{regularFindings.length} finding{regularFindings.length !== 1 ? 's' : ''}</span>
            </p>
          </div>

          {/* Severity summary pills */}
          <div className="flex items-center gap-2 flex-wrap">
            {criticals.length > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border bg-red-500/15 border-red-500/30 text-red-400">
                <XCircle className="w-3 h-3" /> {criticals.length} CRITICAL
              </span>
            )}
            {warnings.length > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border bg-amber-500/15 border-amber-500/30 text-amber-400">
                <AlertTriangle className="w-3 h-3" /> {warnings.length} WARNING
              </span>
            )}
            {infos.length > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border bg-blue-500/15 border-blue-500/30 text-blue-400">
                <Info className="w-3 h-3" /> {infos.length} INFO
              </span>
            )}
          </div>
        </div>

        {/* Filter + refresh + export row */}
        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-theme-border flex-wrap">
          {/* View toggle */}
          <div className="flex items-center rounded-lg border border-theme-border overflow-hidden text-[10px] font-mono flex-shrink-0">
            <button
              onClick={() => setBriefView(false)}
              className={`flex items-center gap-1.5 px-3 py-1.5 transition-colors ${
                !briefView
                  ? 'bg-theme-border/50 text-theme-text'
                  : 'text-theme-text-muted hover:text-theme-text hover:bg-theme-border/20'
              }`}
            >
              <LayoutList className="w-3 h-3" /> FINDINGS
            </button>
            <button
              onClick={() => setBriefView(true)}
              className={`flex items-center gap-1.5 px-3 py-1.5 border-l border-theme-border transition-colors ${
                briefView
                  ? 'bg-theme-border/50 text-theme-text'
                  : 'text-theme-text-muted hover:text-theme-text hover:bg-theme-border/20'
              }`}
            >
              <ClipboardList className="w-3 h-3" /> BRIEF
            </button>
          </div>
          {!briefView && (
            <button
              onClick={() => setShowReviewOnly((v) => !v)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono rounded-lg border transition-colors ${
                showReviewOnly
                  ? 'bg-amber-500/15 border-amber-500/40 text-amber-400'
                  : 'border-theme-border text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30'
              }`}
            >
              {showReviewOnly ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              NEEDS REVIEW ({reviewCount})
            </button>
          )}
          <button
            onClick={fetchFindings}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border border-theme-border rounded-lg text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> REFRESH
          </button>
          {/* Export buttons */}
          <div className="ml-auto flex items-center gap-2">
              <a
              href={`${BACKEND_URL}/api/v1/engagements/${engagement.id}/export/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border
                         border-theme-border rounded-lg text-theme-text-muted
                         hover:text-theme-text hover:bg-theme-border/30 transition-colors"
              title="Download report as PDF"
            >
              <Download className="w-3 h-3" /> PDF
            </a>
            <a
              href={`${BACKEND_URL}/api/v1/engagements/${engagement.id}/export/excel`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border
                         border-green-500/30 rounded-lg text-green-400/70
                         hover:text-green-400 hover:bg-green-500/10 transition-colors"
              title="Download financial model as Excel workbook"
            >
              <Download className="w-3 h-3" /> EXCEL
            </a>
            <button
              onClick={handleSheetsExport}
              disabled={sheetsLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border
                         border-emerald-500/30 rounded-lg text-emerald-400/70
                         hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed"
              title="Export to Google Sheets (requires Google service account credentials)"
            >
              {sheetsLoading
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <FileSpreadsheet className="w-3 h-3" />}
              {sheetsLoading ? 'EXPORTING...' : 'SHEETS'}
            </button>
            <button
              onClick={handleDriveExport}
              disabled={driveLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border
                         border-blue-500/30 rounded-lg text-blue-400/70
                         hover:text-blue-400 hover:bg-blue-500/10 transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed"
              title="Upload PDF + Excel to Google Drive (requires Google service account credentials)"
            >
              {driveLoading
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <HardDrive className="w-3 h-3" />}
              {driveLoading ? 'UPLOADING...' : 'DRIVE'}
            </button>
          </div>
        </div>
      </div>

      {/* TinyFish attribution footer */}
      <div className="flex items-center justify-between px-4 py-3 border border-cyan-500/20 rounded-xl bg-cyan-500/5">
        <div className="flex items-center gap-2">
          <span className="text-base">🐟</span>
          <span className="text-[10px] font-mono text-cyan-400">
            Browser extractions powered by <span className="font-semibold">TinyFish</span> — autonomous browser automation for closed enterprise systems
          </span>
        </div>
        <a
          href="https://tinyfish.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] font-mono text-cyan-400/60 hover:text-cyan-400 transition-colors flex-shrink-0"
        >
          tinyfish.ai →
        </a>
      </div>

      {briefView ? (
        <DealBrief engagement={engagement} findings={findings} />
      ) : (
        <>
          {/* Executive Summary — pinned at top if present */}
          {execSummaryFinding && (
            <ExecutiveSummaryCard finding={execSummaryFinding} />
          )}

          {regularFindings.length === 0 ? (
            <div className="border border-dashed border-theme-border rounded-xl py-16 text-center space-y-3">
              <div className="w-12 h-12 rounded-full border border-theme-border bg-theme-surface flex items-center justify-center mx-auto">
                <Info className="w-5 h-5 text-theme-text-muted" />
              </div>
              <div>
                <p className="text-sm font-semibold">No findings recorded</p>
                <p className="text-xs text-theme-text-muted font-mono mt-1">
                  The pipeline completed — all data sources cross-checked clean,<br />or results are still propagating. Try refreshing.
                </p>
              </div>
              <button
                onClick={fetchFindings}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono border border-theme-border rounded-lg text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 transition-colors"
              >
                <RefreshCw className="w-3 h-3" /> Refresh findings
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <SeverityGroup severity="critical" findings={criticals} defaultOpen autoExpandCards />
              <SeverityGroup severity="warning"  findings={warnings}  defaultOpen autoExpandCards />
              <SeverityGroup severity="info"     findings={infos} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
