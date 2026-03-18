import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Loader2, Trash2, ShieldCheck, AlertTriangle, AlertCircle, Upload, FileText } from 'lucide-react';
import {
  externalRecordsApi,
  legalFindingsApi,
  type ExternalRecord,
  type ConfidenceResult,
  type LegalFinding,
  type LegalRiskSummary,
} from '../../lib/apiClient';

interface Props {
  engagementId: string;
  companyName: string;
  readOnly?: boolean;
}

const RISK_COLOR: Record<string, string> = {
  critical: 'text-red-500',
  high:     'text-red-400',
  medium:   'text-amber-400',
  low:      'text-green-400',
  none:     'text-theme-text-muted',
};

const RISK_BORDER: Record<string, string> = {
  critical: 'border-red-500/40',
  high:     'border-red-400/30',
  medium:   'border-amber-400/30',
  low:      'border-green-400/30',
  none:     'border-theme-border',
};

const SOURCE_LABEL: Record<string, string> = {
  courtlistener: 'Court',
  uspto:         'Patent',
  ucc:           'UCC',
  bank_statement:'Bank',
};

export default function ExternalVerificationPanel({ engagementId, companyName, readOnly = false }: Props) {
  const [records, setRecords]         = useState<ExternalRecord[]>([]);
  const [confidence, setConfidence]   = useState<ConfidenceResult | null>(null);
  const [findings, setFindings]       = useState<LegalFinding[]>([]);
  const [riskSummary, setRiskSummary] = useState<LegalRiskSummary | null>(null);
  const [loading, setLoading]         = useState(true);
  const [fetchingCourt, setFetchingCourt]   = useState(false);
  const [fetchingPatents, setFetchingPatents] = useState(false);
  const [uploadingBank, setUploadingBank]   = useState(false);
  const [analyzingLegal, setAnalyzingLegal] = useState(false);
  const [deletingId, setDeletingId]   = useState<string | null>(null);
  const [updatingId, setUpdatingId]   = useState<string | null>(null);
  const bankInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [recs, conf, finds, risk] = await Promise.all([
        externalRecordsApi.list(engagementId),
        externalRecordsApi.confidence(engagementId),
        legalFindingsApi.list(engagementId),
        legalFindingsApi.riskSummary(engagementId),
      ]);
      setRecords(recs);
      setConfidence(conf);
      setFindings(finds);
      setRiskSummary(risk);
    } catch { /* ignore */ }
    setLoading(false);
  }, [engagementId]);

  useEffect(() => { load(); }, [load]);

  const fetchCourt = async () => {
    setFetchingCourt(true);
    try {
      const added = await externalRecordsApi.fetchCourt(engagementId, companyName);
      setRecords((prev) => [...added, ...prev]);
      const conf = await externalRecordsApi.confidence(engagementId);
      setConfidence(conf);
    } catch { /* ignore */ }
    setFetchingCourt(false);
  };

  const fetchPatents = async () => {
    setFetchingPatents(true);
    try {
      const added = await externalRecordsApi.fetchPatents(engagementId, companyName);
      setRecords((prev) => [...added, ...prev]);
      const conf = await externalRecordsApi.confidence(engagementId);
      setConfidence(conf);
    } catch { /* ignore */ }
    setFetchingPatents(false);
  };

  const uploadBank = async (file: File) => {
    setUploadingBank(true);
    try {
      const added = await externalRecordsApi.uploadBankStatement(engagementId, file);
      setRecords((prev) => [added, ...prev]);
    } catch { /* ignore */ }
    setUploadingBank(false);
  };

  const analyzeAll = async () => {
    setAnalyzingLegal(true);
    try {
      const newFindings = await legalFindingsApi.analyzeAll(engagementId);
      setFindings(newFindings);
      const risk = await legalFindingsApi.riskSummary(engagementId);
      setRiskSummary(risk);
    } catch { /* ignore */ }
    setAnalyzingLegal(false);
  };

  const toggleReviewed = async (f: LegalFinding) => {
    setUpdatingId(f.id);
    try {
      const updated = await legalFindingsApi.update(engagementId, f.id, { reviewed: !f.reviewed });
      setFindings((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch { /* ignore */ }
    setUpdatingId(null);
  };

  const deleteRecord = async (id: string) => {
    setDeletingId(id);
    try {
      await externalRecordsApi.delete(engagementId, id);
      setRecords((prev) => prev.filter((r) => r.id !== id));
      const conf = await externalRecordsApi.confidence(engagementId);
      setConfidence(conf);
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

  const pct = (n: number) => Math.round(n * 100);

  return (
    <div className="space-y-6">
      {/* ── External Records Section ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-400" />
              External Verification
            </h3>
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
              Court records · patents · bank statements
            </p>
          </div>
          {/* Confidence score badge */}
          {confidence && (
            <div className="flex items-center gap-3">
              <div className="text-center border border-theme-border rounded-lg px-3 py-2">
                <p className="text-lg font-bold font-mono text-theme-text">{pct(confidence.overall_confidence)}%</p>
                <p className="text-[9px] font-mono text-theme-text-muted">CONFIDENCE</p>
              </div>
              <div className="text-center border border-theme-border rounded-lg px-3 py-2">
                <p className="text-lg font-bold font-mono text-theme-text">{pct(confidence.source_independence)}%</p>
                <p className="text-[9px] font-mono text-theme-text-muted">INDEPENDENCE</p>
              </div>
            </div>
          )}
        </div>

        {/* Action buttons */}
        {!readOnly && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={fetchCourt}
              disabled={fetchingCourt}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                         text-[10px] font-mono hover:bg-theme-border/30 transition-colors disabled:opacity-40"
            >
              {fetchingCourt ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
              SEARCH COURT RECORDS
            </button>
            <button
              onClick={fetchPatents}
              disabled={fetchingPatents}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                         text-[10px] font-mono hover:bg-theme-border/30 transition-colors disabled:opacity-40"
            >
              {fetchingPatents ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
              SEARCH PATENTS
            </button>
            <button
              onClick={() => bankInputRef.current?.click()}
              disabled={uploadingBank}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                         text-[10px] font-mono hover:bg-theme-border/30 transition-colors disabled:opacity-40"
            >
              {uploadingBank ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
              UPLOAD BANK STATEMENT
            </button>
            <input
              ref={bankInputRef}
              type="file"
              accept=".pdf,.txt"
              className="hidden"
              onChange={(e) => { if (e.target.files?.[0]) uploadBank(e.target.files[0]); }}
            />
          </div>
        )}

        {/* Records list */}
        {records.length === 0 ? (
          <div className="border border-dashed border-theme-border rounded-xl p-8 text-center">
            <ShieldCheck className="w-6 h-6 text-theme-text-muted mx-auto mb-2" />
            <p className="text-xs font-mono text-theme-text-muted">No external records yet. Use the buttons above to fetch data.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {records.map((r) => (
              <div
                key={r.id}
                className={`border rounded-xl px-4 py-3 ${RISK_BORDER[r.risk_level] ?? 'border-theme-border'}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[9px] font-mono px-1.5 py-0.5 border border-theme-border rounded text-theme-text-muted flex-shrink-0">
                        {SOURCE_LABEL[r.source] ?? r.source.toUpperCase()}
                      </span>
                      <span className="text-[9px] font-mono text-theme-text-muted flex-shrink-0">
                        {r.record_type}
                      </span>
                      <span className={`text-[10px] font-mono font-semibold flex-shrink-0 ${RISK_COLOR[r.risk_level] ?? ''}`}>
                        {r.risk_level.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs font-semibold mt-1 truncate">{r.title}</p>
                    {r.description && (
                      <p className="text-[11px] font-mono text-theme-text-muted mt-0.5 line-clamp-2">{r.description}</p>
                    )}
                    {r.url && (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] font-mono text-blue-400 hover:underline mt-0.5 block truncate"
                      >
                        {r.url}
                      </a>
                    )}
                  </div>
                  {!readOnly && (
                    <button
                      onClick={() => deleteRecord(r.id)}
                      disabled={deletingId === r.id}
                      className="p-1.5 text-theme-text-muted hover:text-red-400 hover:bg-red-500/10 rounded transition-colors flex-shrink-0"
                    >
                      {deletingId === r.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Legal Analysis Section ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4 text-amber-400" />
              Legal Analysis
            </h3>
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
              Contract clause scanning · risk flagging · review tracking
            </p>
          </div>
          {!readOnly && (
            <button
              onClick={analyzeAll}
              disabled={analyzingLegal}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30
                         text-amber-400 text-[10px] font-mono rounded-lg hover:bg-amber-500/20
                         transition-colors disabled:opacity-40"
            >
              {analyzingLegal ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
              ANALYZE ALL DOCUMENTS
            </button>
          )}
        </div>

        {/* Risk summary */}
        {riskSummary && riskSummary.total > 0 && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[
              { label: 'Total',      value: riskSummary.total,      color: 'text-theme-text' },
              { label: 'Critical',   value: riskSummary.critical,   color: 'text-red-500' },
              { label: 'High',       value: riskSummary.high,       color: 'text-red-400' },
              { label: 'Medium',     value: riskSummary.medium,     color: 'text-amber-400' },
              { label: 'Low',        value: riskSummary.low,        color: 'text-green-400' },
              { label: 'Unreviewed', value: riskSummary.unreviewed, color: 'text-theme-text-muted' },
            ].map(({ label, value, color }) => (
              <div key={label} className="border border-theme-border rounded-lg p-2 text-center">
                <p className={`text-base font-bold font-mono ${color}`}>{value}</p>
                <p className="text-[9px] font-mono text-theme-text-muted mt-0.5">{label.toUpperCase()}</p>
              </div>
            ))}
          </div>
        )}

        {/* Findings list */}
        {findings.length === 0 ? (
          <div className="border border-dashed border-theme-border rounded-xl p-8 text-center">
            <AlertCircle className="w-6 h-6 text-theme-text-muted mx-auto mb-2" />
            <p className="text-xs font-mono text-theme-text-muted">
              No findings yet. Upload documents and click ANALYZE ALL DOCUMENTS.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {findings.map((f) => (
              <div
                key={f.id}
                className={`border rounded-xl px-4 py-3 ${RISK_BORDER[f.risk_level] ?? 'border-theme-border'} ${f.reviewed ? 'opacity-60' : ''}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[9px] font-mono px-1.5 py-0.5 border border-theme-border rounded text-theme-text-muted">
                        {f.clause_type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className={`text-[10px] font-mono font-semibold ${RISK_COLOR[f.risk_level] ?? ''}`}>
                        {f.risk_level.toUpperCase()}
                      </span>
                      {f.requires_review && !f.reviewed && (
                        <span className="flex items-center gap-0.5 text-[9px] font-mono text-amber-400">
                          <AlertTriangle className="w-2.5 h-2.5" /> NEEDS REVIEW
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-mono text-theme-text mt-1.5 line-clamp-3 italic">
                      "{f.text_excerpt}"
                    </p>
                  </div>
                  {!readOnly && (
                    <button
                      onClick={() => toggleReviewed(f)}
                      disabled={updatingId === f.id}
                      title={f.reviewed ? 'Mark as unreviewed' : 'Mark as reviewed'}
                      className={`p-1.5 rounded transition-colors flex-shrink-0 ${
                        f.reviewed
                          ? 'text-green-400 hover:text-theme-text-muted'
                          : 'text-theme-text-muted hover:text-green-400'
                      }`}
                    >
                      {updatingId === f.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <ShieldCheck className="w-3.5 h-3.5" />
                      }
                    </button>
                  )}
                </div>
                {f.notes && (
                  <p className="text-[11px] font-mono text-theme-text-muted mt-2">{f.notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
