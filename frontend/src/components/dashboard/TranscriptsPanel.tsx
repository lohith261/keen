import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Download,
  FileText, Loader2, MessageSquare, Minus, Plus, Search, Trash2, TrendingUp, Upload, X,
} from 'lucide-react';

const BACKEND_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
const API_BASE = `${BACKEND_URL}/api/v1`;

interface TranscriptRecord {
  id: string;
  engagement_id: string;
  source: string;
  external_id: string | null;
  title: string;
  expert_name: string | null;
  expert_role: string | null;
  call_date: string | null;
  company_name: string | null;
  sentiment: 'positive' | 'neutral' | 'negative' | null;
  key_themes: string[] | null;
  extracted_insights: string | null;
  file_size_bytes: number | null;
  status: 'processing' | 'ready' | 'error';
  error_message: string | null;
  created_at: string;
}

interface Props {
  engagementId: string;
  companyName: string;
  readOnly?: boolean;
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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const SENTIMENT_CONFIG = {
  positive: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30', label: 'POSITIVE' },
  neutral:  { color: 'text-blue-400',  bg: 'bg-blue-500/10',  border: 'border-blue-500/30',  label: 'NEUTRAL' },
  negative: { color: 'text-red-400',   bg: 'bg-red-500/10',   border: 'border-red-500/30',   label: 'NEGATIVE' },
};

const SOURCE_LABELS: Record<string, string> = {
  tegus: 'Tegus',
  third_bridge: 'Third Bridge',
  manual_upload: 'Manual Upload',
};

function TranscriptCard({
  transcript,
  onDelete,
}: {
  transcript: TranscriptRecord;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const sentCfg = transcript.sentiment ? SENTIMENT_CONFIG[transcript.sentiment] : null;

  const handleDelete = async () => {
    setDeleting(true);
    await onDelete(transcript.id);
    setDeleting(false);
  };

  return (
    <div className="border border-theme-border rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-theme-border/20 transition-colors"
      >
        <MessageSquare className="w-4 h-4 text-theme-text-muted flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold leading-snug truncate">{transcript.title}</p>
          <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
            {SOURCE_LABELS[transcript.source] ?? transcript.source}
            {transcript.expert_name && ` · ${transcript.expert_name}`}
            {transcript.expert_role && ` (${transcript.expert_role})`}
            {transcript.call_date && ` · ${new Date(transcript.call_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {transcript.status === 'processing' && (
            <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" /> PROCESSING
            </span>
          )}
          {transcript.status === 'error' && (
            <span className="flex items-center gap-1 text-[10px] font-mono text-red-400">
              <AlertCircle className="w-3 h-3" /> ERROR
            </span>
          )}
          {sentCfg && (
            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${sentCfg.bg} ${sentCfg.border} ${sentCfg.color}`}>
              {sentCfg.label}
            </span>
          )}
          {expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted" />
            : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted" />
          }
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 border-t border-theme-border bg-theme-bg/40 space-y-3">
          {transcript.key_themes && transcript.key_themes.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1.5">Key Themes</p>
              <div className="flex flex-wrap gap-1.5">
                {transcript.key_themes.map((theme, i) => (
                  <span
                    key={i}
                    className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-theme-border text-theme-text-muted"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            </div>
          )}

          {transcript.extracted_insights && (
            <div>
              <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1">Extracted Insights</p>
              <p className="text-[11px] text-theme-text leading-relaxed">{transcript.extracted_insights}</p>
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            {transcript.file_size_bytes != null && (
              <span className="text-[10px] font-mono text-theme-text-muted/60">
                {formatBytes(transcript.file_size_bytes)}
              </span>
            )}
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="ml-auto flex items-center gap-1 text-[10px] font-mono text-theme-text-muted
                         hover:text-red-400 transition-colors disabled:opacity-40"
            >
              {deleting
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <Trash2 className="w-3 h-3" />
              }
              DELETE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FetchForm({
  engagementId,
  companyName,
  onFetched,
  onCancel,
}: {
  engagementId: string;
  companyName: string;
  onFetched: (transcripts: TranscriptRecord[]) => void;
  onCancel: () => void;
}) {
  const [source, setSource] = useState<'tegus' | 'third_bridge'>('tegus');
  const [query, setQuery] = useState(companyName);
  const [max, setMax] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFetch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const resp = await fetch(`${API_BASE}/engagements/${engagementId}/transcripts/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ source, company_name: query, max_transcripts: max }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `HTTP ${resp.status}`);
      }
      const fetched = await resp.json() as TranscriptRecord[];
      onFetched(fetched);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleFetch} className="border border-theme-border rounded-xl p-4 space-y-3 bg-theme-bg/40">
      <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">Fetch from Expert Network</p>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Source</label>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as 'tegus' | 'third_bridge')}
            className="w-full px-3 py-2 bg-theme-bg border border-theme-border rounded-lg text-xs
                       focus:outline-none focus:border-theme-text-muted transition-colors"
          >
            <option value="tegus">Tegus</option>
            <option value="third_bridge">Third Bridge</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Max Transcripts</label>
          <input
            type="number"
            min={1}
            max={50}
            value={max}
            onChange={(e) => setMax(Number(e.target.value))}
            className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-xs
                       focus:outline-none focus:border-theme-text-muted transition-colors"
          />
        </div>
      </div>

      <div>
        <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">Company Search Query</label>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
          className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-xs
                     focus:outline-none focus:border-theme-text-muted transition-colors"
        />
      </div>

      <p className="text-[10px] font-mono text-amber-400/80">
        Requires {source === 'tegus' ? 'Tegus API key' : 'Third Bridge client credentials'} in the Credentials panel
      </p>

      {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

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
          disabled={loading || !query.trim()}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-theme-text text-theme-bg text-[10px] font-mono font-semibold
                     rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
          FETCH
        </button>
      </div>
    </form>
  );
}

export default function TranscriptsPanel({ engagementId, companyName, readOnly = false }: Props) {
  const [transcripts, setTranscripts] = useState<TranscriptRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showFetchForm, setShowFetchForm] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadTranscripts = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/engagements/${engagementId}/transcripts`, {
        headers: authHeaders(),
      });
      if (resp.ok) setTranscripts(await resp.json());
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [engagementId]);

  useEffect(() => { loadTranscripts(); }, [loadTranscripts]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadError(null);
    setUploading(true);

    const errors: string[] = [];
    for (const file of Array.from(files)) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const resp = await fetch(`${API_BASE}/engagements/${engagementId}/transcripts`, {
          method: 'POST',
          headers: authHeaders(),
          body: formData,
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error((err as { detail?: string }).detail || `HTTP ${resp.status}`);
        }
        const t = await resp.json() as TranscriptRecord;
        setTranscripts((prev) => [t, ...prev]);
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof Error ? err.message : 'failed'}`);
      }
    }
    if (errors.length > 0) setUploadError(errors.join(' · '));
    setUploading(false);
  };

  const handleDelete = async (transcriptId: string) => {
    try {
      await fetch(`${API_BASE}/engagements/${engagementId}/transcripts/${transcriptId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setTranscripts((prev) => prev.filter((t) => t.id !== transcriptId));
    } catch { /* ignore */ }
  };

  const handleFetched = (fetched: TranscriptRecord[]) => {
    setTranscripts((prev) => [...fetched, ...prev]);
    setShowFetchForm(false);
  };

  // Stats
  const positive = transcripts.filter((t) => t.sentiment === 'positive').length;
  const negative = transcripts.filter((t) => t.sentiment === 'negative').length;
  const neutral  = transcripts.filter((t) => t.sentiment === 'neutral').length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="text-sm font-semibold">Expert Call Transcripts</h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            {readOnly
              ? 'Expert call transcripts included in analysis'
              : 'Upload transcripts or fetch from Tegus / Third Bridge — included in the analysis pipeline'}
          </p>
        </div>
        {!readOnly && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFetchForm((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                         text-[10px] font-mono text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 transition-colors"
            >
              <Search className="w-3 h-3" /> FETCH
            </button>
            <button
              onClick={() => inputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-theme-border rounded-lg
                         text-[10px] font-mono text-theme-text-muted hover:text-theme-text hover:bg-theme-border/30 transition-colors"
            >
              <Upload className="w-3 h-3" /> UPLOAD
            </button>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      {!readOnly && (
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.pdf"
          multiple
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
      )}

      {/* Upload error */}
      {uploadError && (
        <div className="flex items-center gap-2 text-xs text-red-400 font-mono">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-auto">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Fetch form */}
      {showFetchForm && (
        <FetchForm
          engagementId={engagementId}
          companyName={companyName}
          onFetched={handleFetched}
          onCancel={() => setShowFetchForm(false)}
        />
      )}

      {/* Sentiment summary */}
      {transcripts.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          <div className="border border-green-500/30 bg-green-500/8 rounded-xl px-3 py-2.5 text-center">
            <p className="text-lg font-bold text-green-400">{positive}</p>
            <p className="text-[10px] font-mono text-green-400/70 mt-0.5">POSITIVE</p>
          </div>
          <div className="border border-blue-500/30 bg-blue-500/8 rounded-xl px-3 py-2.5 text-center">
            <p className="text-lg font-bold text-blue-400">{neutral}</p>
            <p className="text-[10px] font-mono text-blue-400/70 mt-0.5">NEUTRAL</p>
          </div>
          <div className="border border-red-500/30 bg-red-500/8 rounded-xl px-3 py-2.5 text-center">
            <p className="text-lg font-bold text-red-400">{negative}</p>
            <p className="text-[10px] font-mono text-red-400/70 mt-0.5">NEGATIVE</p>
          </div>
        </div>
      )}

      {uploading && (
        <div className="flex items-center gap-2 text-xs font-mono text-theme-text-muted">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading…
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-theme-text-muted" />
        </div>
      )}

      {!loading && transcripts.length === 0 && !showFetchForm && (
        <div className="border border-dashed border-theme-border rounded-xl p-10 text-center space-y-3">
          <MessageSquare className="w-7 h-7 text-theme-text-muted mx-auto" />
          <div>
            <p className="text-sm font-semibold">No expert transcripts</p>
            <p className="text-xs text-theme-text-muted font-mono mt-1">
              Upload TXT/PDF files or fetch directly from Tegus or Third Bridge
            </p>
          </div>
          {!readOnly && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setShowFetchForm(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-theme-border
                           text-xs font-mono rounded-lg hover:bg-theme-border/30 transition-colors text-theme-text-muted"
              >
                <Search className="w-3 h-3" /> FETCH FROM TEGUS / THIRD BRIDGE
              </button>
              <button
                onClick={() => inputRef.current?.click()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-theme-text text-theme-bg
                           text-xs font-mono font-semibold rounded-lg hover:opacity-90 transition-opacity"
              >
                <Upload className="w-3 h-3" /> UPLOAD TRANSCRIPT
              </button>
            </div>
          )}
        </div>
      )}

      {!loading && transcripts.length > 0 && (
        <div className="space-y-2">
          {transcripts.map((t) => (
            <TranscriptCard key={t.id} transcript={t} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
