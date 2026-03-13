import { useState } from 'react';
import {
  CheckCircle2, AlertTriangle, XCircle, Info, ChevronDown, ChevronRight,
  TrendingUp, Users, BarChart3, FileText, ThumbsUp, ThumbsDown, Minus,
} from 'lucide-react';
import type { Engagement } from '../../lib/apiClient';

interface Props {
  engagement: Engagement;
}

type FindingItem = {
  title?: string;
  description?: string;
  type?: string;
  severity?: string;
  metric?: string;
  notes?: string;
  impact?: string;
};

function RecommendationBadge({ rec }: { rec: string }) {
  if (!rec) return null;
  const lower = rec.toLowerCase();
  if (lower.includes('proceed') || lower.includes('recommend') || lower.includes('invest')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold
                       bg-green-500/15 border border-green-500/30 text-green-400">
        <ThumbsUp className="w-3.5 h-3.5" /> {rec}
      </span>
    );
  }
  if (lower.includes('pass') || lower.includes('decline') || lower.includes('reject')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold
                       bg-red-500/15 border border-red-500/30 text-red-400">
        <ThumbsDown className="w-3.5 h-3.5" /> {rec}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold
                     bg-amber-500/15 border border-amber-500/30 text-amber-400">
      <Minus className="w-3.5 h-3.5" /> {rec}
    </span>
  );
}

function SeverityIcon({ severity }: { severity: string }) {
  const s = severity?.toLowerCase();
  if (s === 'critical') return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
  if (s === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />;
  return <Info className="w-4 h-4 text-blue-400 flex-shrink-0" />;
}

function CollapsibleSection({
  title,
  icon: Icon,
  count,
  children,
  defaultOpen = false,
}: {
  title: string;
  icon: React.ElementType;
  count?: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-theme-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-theme-bg/60 hover:bg-theme-border/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-theme-text-muted" />
          <span className="text-xs font-semibold tracking-wide">{title}</span>
          {count !== undefined && (
            <span className="px-2 py-0.5 rounded-full bg-theme-border text-[10px] font-mono text-theme-text-muted">
              {count}
            </span>
          )}
        </div>
        {open ? (
          <ChevronDown className="w-4 h-4 text-theme-text-muted" />
        ) : (
          <ChevronRight className="w-4 h-4 text-theme-text-muted" />
        )}
      </button>
      {open && <div className="px-5 py-4 space-y-3">{children}</div>}
    </div>
  );
}

export default function ResultsPanel({ engagement }: Props) {
  const config = engagement.config ?? {};
  const pipelineData = (config.pipeline_data ?? {}) as Record<string, unknown>;
  const deliveryResult = (pipelineData.delivery ?? {}) as Record<string, unknown>;
  const analysisResult = (pipelineData.analysis ?? {}) as Record<string, unknown>;

  // Extract nested results from compile steps
  const execSummaryRaw = (deliveryResult.finalize_delivery as Record<string, unknown>)
    ?? (deliveryResult.generate_executive_summary as Record<string, unknown>)
    ?? {};
  const execSummary = ((execSummaryRaw as Record<string, unknown>)?.executive_summary
    ?? execSummaryRaw) as Record<string, unknown>;

  const analysisData = ((analysisResult.compile_analysis as Record<string, unknown>)
    ?.analysis_summary ?? analysisResult) as Record<string, unknown>;

  const keyFindings = (execSummary.key_findings ?? []) as FindingItem[];
  const riskAssessment = execSummary.risk_assessment as string ?? '';
  const recommendation = execSummary.recommendation as string ?? '';
  const recommendationRationale = execSummary.recommendation_rationale as string ?? '';

  const revenueVariances = (analysisData.revenue_variances ?? []) as FindingItem[];
  const costVariances = (analysisData.cost_variances ?? []) as FindingItem[];
  const crossRefs = (analysisData.cross_references ?? {}) as Record<string, unknown>;
  const overallConfidence = (analysisData.overall_confidence as number) ?? 0;

  const hasResults = keyFindings.length > 0 || revenueVariances.length > 0 || recommendation;

  if (!hasResults) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
        <CheckCircle2 className="w-10 h-10 text-green-400" />
        <p className="text-sm font-semibold">Pipeline completed</p>
        <p className="text-xs text-theme-text-muted font-mono">
          Results are being processed — reload to refresh
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="border border-theme-border rounded-xl p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold">{engagement.company_name} — Due Diligence Summary</h3>
            <p className="text-[11px] font-mono text-theme-text-muted mt-1">
              {engagement.completed_at
                ? `Completed ${new Date(engagement.completed_at).toLocaleString()}`
                : 'Completed'}
              {overallConfidence > 0 && ` · Confidence: ${(overallConfidence * 100).toFixed(0)}%`}
            </p>
          </div>
          <RecommendationBadge rec={recommendation} />
        </div>

        {riskAssessment && (
          <div className="bg-theme-border/30 rounded-lg px-4 py-3">
            <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1">
              Risk Assessment
            </p>
            <p className="text-xs text-theme-text">{riskAssessment}</p>
          </div>
        )}

        {recommendationRationale && (
          <div className="bg-theme-border/30 rounded-lg px-4 py-3">
            <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1">
              Rationale
            </p>
            <p className="text-xs text-theme-text">{recommendationRationale}</p>
          </div>
        )}
      </div>

      {/* Key findings */}
      {keyFindings.length > 0 && (
        <CollapsibleSection
          title="KEY FINDINGS"
          icon={CheckCircle2}
          count={keyFindings.length}
          defaultOpen
        >
          <div className="space-y-2">
            {keyFindings.map((f, i) => (
              <div
                key={i}
                className="flex gap-3 items-start p-3 rounded-lg border border-theme-border bg-theme-bg/40"
              >
                <SeverityIcon severity={f.severity ?? 'info'} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium">{f.title ?? f.metric}</p>
                  {(f.description ?? f.notes ?? f.impact) && (
                    <p className="text-[11px] text-theme-text-muted mt-1">
                      {f.description ?? f.notes ?? f.impact}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Revenue variances */}
      {revenueVariances.length > 0 && (
        <CollapsibleSection
          title="REVENUE VARIANCES"
          icon={TrendingUp}
          count={revenueVariances.length}
        >
          <div className="space-y-2">
            {revenueVariances.map((v, i) => (
              <div
                key={i}
                className="flex gap-3 items-start p-3 rounded-lg border border-theme-border bg-theme-bg/40"
              >
                <SeverityIcon severity={v.severity ?? 'warning'} />
                <div>
                  <p className="text-xs font-medium">{v.title}</p>
                  {v.description && (
                    <p className="text-[11px] text-theme-text-muted mt-1">{v.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Cost variances */}
      {costVariances.length > 0 && (
        <CollapsibleSection
          title="COST VARIANCES"
          icon={BarChart3}
          count={costVariances.length}
        >
          <div className="space-y-2">
            {costVariances.map((v, i) => (
              <div
                key={i}
                className="flex gap-3 items-start p-3 rounded-lg border border-theme-border bg-theme-bg/40"
              >
                <SeverityIcon severity={v.severity ?? 'warning'} />
                <div>
                  <p className="text-xs font-medium">{v.title}</p>
                  {v.description && (
                    <p className="text-[11px] text-theme-text-muted mt-1">{v.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Cross-references */}
      {(crossRefs as Record<string, unknown[]>).crm_erp_overlap?.length > 0 && (
        <CollapsibleSection
          title="CROSS-REFERENCE DISCREPANCIES"
          icon={Users}
          count={(crossRefs as Record<string, unknown[]>).crm_erp_overlap?.length}
        >
          <div className="space-y-2">
            {((crossRefs as Record<string, unknown[]>).crm_erp_overlap ?? []).map((xref: unknown, i: number) => {
              const x = xref as Record<string, unknown>;
              return (
                <div
                  key={i}
                  className="flex gap-3 items-start p-3 rounded-lg border border-theme-border bg-theme-bg/40"
                >
                  <SeverityIcon severity="warning" />
                  <div>
                    <p className="text-xs font-medium">{x.metric as string}</p>
                    {x.notes && (
                      <p className="text-[11px] text-theme-text-muted mt-1">{x.notes as string}</p>
                    )}
                    {x.match_quality !== undefined && (
                      <p className="text-[10px] font-mono text-theme-text-muted mt-1">
                        Match quality: {((x.match_quality as number) * 100).toFixed(0)}%
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CollapsibleSection>
      )}

      {/* Report sections placeholder */}
      <CollapsibleSection title="DETAILED REPORT" icon={FileText}>
        <p className="text-xs text-theme-text-muted font-mono">
          The full 9-section report is available in the pipeline output.
          View the complete report via the API: <code className="bg-theme-border px-1.5 py-0.5 rounded">
            GET /api/v1/engagements/{engagement.id}
          </code>
        </p>
      </CollapsibleSection>
    </div>
  );
}
