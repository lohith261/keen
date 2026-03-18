import { useEffect, useRef, useState } from 'react';
import { X, FlaskConical, Radio, Loader2, ChevronDown, ChevronRight, Building2 } from 'lucide-react';
import { engagementsApi, type Engagement } from '../../lib/apiClient';
import { useDemoMode } from '../../context/DemoModeContext';

interface EdgarHit {
  entity_name: string;
  file_date: string;
}

async function searchEdgar(query: string): Promise<string[]> {
  if (query.length < 2) return [];
  try {
    const url = `https://efts.sec.gov/LATEST/search-index?entity=${encodeURIComponent(query)}&forms=10-K`;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) return [];
    const data = await res.json() as { hits?: { hits?: { _source?: EdgarHit }[] } };
    const hits = data?.hits?.hits ?? [];
    const seen = new Set<string>();
    const names: string[] = [];
    for (const h of hits) {
      const name = h._source?.entity_name;
      if (name && !seen.has(name)) { seen.add(name); names.push(name); }
      if (names.length >= 6) break;
    }
    return names;
  } catch {
    return [];
  }
}

interface Props {
  onClose: () => void;
  onCreated: (engagement: Engagement) => void;
}

const ENGAGEMENT_TYPES = [
  { value: 'full_diligence', label: 'Full Due Diligence' },
  { value: 'commercial_only', label: 'Commercial Only' },
  { value: 'financial_only', label: 'Financial Only' },
  { value: 'quick_scan', label: 'Quick Scan' },
];

export default function NewEngagementModal({ onClose, onCreated }: Props) {
  const { isDemoMode } = useDemoMode();
  const [form, setForm] = useState({
    company_name: '',
    pe_firm: '',
    deal_size: '',
    engagement_type: 'full_diligence',
    notes: '',
  });
  const [edgarSuggestions, setEdgarSuggestions] = useState<string[]>([]);
  const [edgarLoading, setEdgarLoading] = useState(false);
  const edgarTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const suppressEdgar = useRef(false);
  const [distribution, setDistribution] = useState({
    slack_webhook_url: '',
    email_recipients: '',
    sharepoint_site_url: '',
    sharepoint_tenant_id: '',
    sharepoint_client_id: '',
    sharepoint_client_secret: '',
    sharepoint_folder: 'KEEN Reports',
  });
  const [showDistribution, setShowDistribution] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Debounced SEC EDGAR company lookup
  useEffect(() => {
    if (suppressEdgar.current) { suppressEdgar.current = false; return; }
    if (edgarTimer.current) clearTimeout(edgarTimer.current);
    const q = form.company_name.trim();
    if (q.length < 2) { setEdgarSuggestions([]); return; }
    edgarTimer.current = setTimeout(async () => {
      setEdgarLoading(true);
      const names = await searchEdgar(q);
      setEdgarSuggestions(names);
      setEdgarLoading(false);
    }, 350);
    return () => { if (edgarTimer.current) clearTimeout(edgarTimer.current); };
  }, [form.company_name]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setLoading(true);
    setError('');
    try {
      // Build distribution config — only include non-empty fields
      const distConfig: Record<string, string> = {};
      if (distribution.slack_webhook_url.trim())
        distConfig.slack_webhook_url = distribution.slack_webhook_url.trim();
      if (distribution.email_recipients.trim())
        distConfig.email_recipients = distribution.email_recipients.trim();
      if (distribution.sharepoint_site_url.trim())
        distConfig.sharepoint_site_url = distribution.sharepoint_site_url.trim();
      if (distribution.sharepoint_tenant_id.trim())
        distConfig.sharepoint_tenant_id = distribution.sharepoint_tenant_id.trim();
      if (distribution.sharepoint_client_id.trim())
        distConfig.sharepoint_client_id = distribution.sharepoint_client_id.trim();
      if (distribution.sharepoint_client_secret.trim())
        distConfig.sharepoint_client_secret = distribution.sharepoint_client_secret.trim();
      if (distribution.sharepoint_folder.trim())
        distConfig.sharepoint_folder = distribution.sharepoint_folder.trim();

      const engagement = await engagementsApi.create({
        company_name: form.company_name.trim(),
        pe_firm: form.pe_firm.trim() || undefined,
        deal_size: form.deal_size.trim() || undefined,
        notes: form.notes.trim() || undefined,
        config: {
          engagement_type: form.engagement_type,
          ...distConfig,
        },
      });
      await engagementsApi.start(engagement.id);
      onCreated({ ...engagement, status: 'running' });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start engagement');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-theme-bg border border-theme-border rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-theme-border">
          <div>
            <h2 className="text-sm font-semibold tracking-wide">NEW ENGAGEMENT</h2>
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
              Configure and start a due diligence pipeline
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-theme-border transition-colors"
          >
            <X className="w-4 h-4 text-theme-text-muted" />
          </button>
        </div>

        {/* Mode badge */}
        <div className="px-6 pt-4">
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold border ${
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
            {isDemoMode
              ? 'SIMULATION — uses fixture data for demonstration'
              : 'LIVE — pipeline connects to enterprise data sources'}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div className="relative">
            <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
              Target Company *
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                onBlur={() => setTimeout(() => setEdgarSuggestions([]), 150)}
                placeholder="e.g. Zendesk Inc."
                className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                           placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                           transition-colors pr-8"
              />
              {edgarLoading && (
                <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 animate-spin text-theme-text-muted" />
              )}
            </div>
            {edgarSuggestions.length > 0 && (
              <div className="absolute z-10 left-0 right-0 mt-1 border border-theme-border bg-theme-bg rounded-lg shadow-xl overflow-hidden">
                {edgarSuggestions.map((name) => (
                  <button
                    key={name}
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      suppressEdgar.current = true;
                      setForm((f) => ({ ...f, company_name: name }));
                      setEdgarSuggestions([]);
                    }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-left text-xs hover:bg-theme-border/40 transition-colors"
                  >
                    <Building2 className="w-3.5 h-3.5 text-theme-text-muted flex-shrink-0" />
                    <span>{name}</span>
                    <span className="ml-auto text-[10px] font-mono text-theme-text-muted/60">SEC EDGAR</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                PE Firm
              </label>
              <input
                type="text"
                value={form.pe_firm}
                onChange={(e) => setForm((f) => ({ ...f, pe_firm: e.target.value }))}
                placeholder="e.g. Accel Partners"
                className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                           placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                           transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                Deal Size
              </label>
              <input
                type="text"
                value={form.deal_size}
                onChange={(e) => setForm((f) => ({ ...f, deal_size: e.target.value }))}
                placeholder="e.g. $50M"
                className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                           placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                           transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
              Engagement Type
            </label>
            <select
              value={form.engagement_type}
              onChange={(e) => setForm((f) => ({ ...f, engagement_type: e.target.value }))}
              className="w-full px-3 py-2 bg-theme-bg border border-theme-border rounded-lg text-sm
                         focus:outline-none focus:border-theme-text-muted transition-colors"
            >
              {ENGAGEMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
              Notes
            </label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Optional context or instructions for this engagement"
              className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm resize-none
                         placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                         transition-colors"
            />
          </div>

          {/* Distribution config — collapsible */}
          <div className="border border-theme-border rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setShowDistribution((v) => !v)}
              className="flex w-full items-center justify-between px-3 py-2.5 text-left
                         hover:bg-theme-border/20 transition-colors"
            >
              <span className="text-[11px] font-mono text-theme-text-muted uppercase tracking-wider">
                Distribution Channels (optional)
              </span>
              {showDistribution
                ? <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted" />
                : <ChevronRight className="w-3.5 h-3.5 text-theme-text-muted" />
              }
            </button>

            {showDistribution && (
              <div className="border-t border-theme-border px-3 py-3 space-y-3 bg-theme-bg/30">
                <div>
                  <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">
                    Slack Webhook URL
                  </label>
                  <input
                    type="url"
                    value={distribution.slack_webhook_url}
                    onChange={(e) => setDistribution((d) => ({ ...d, slack_webhook_url: e.target.value }))}
                    placeholder="https://hooks.slack.com/services/..."
                    className="w-full px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                               placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono text-theme-text-muted mb-1 uppercase tracking-wider">
                    Email Recipients (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={distribution.email_recipients}
                    onChange={(e) => setDistribution((d) => ({ ...d, email_recipients: e.target.value }))}
                    placeholder="partner@firm.com, analyst@firm.com"
                    className="w-full px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                               placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                  />
                </div>

                <div className="pt-1">
                  <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-2">
                    SharePoint
                  </p>
                  <div className="space-y-2">
                    <input
                      type="url"
                      value={distribution.sharepoint_site_url}
                      onChange={(e) => setDistribution((d) => ({ ...d, sharepoint_site_url: e.target.value }))}
                      placeholder="SharePoint site URL (https://contoso.sharepoint.com/sites/deals)"
                      className="w-full px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                                 placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={distribution.sharepoint_tenant_id}
                        onChange={(e) => setDistribution((d) => ({ ...d, sharepoint_tenant_id: e.target.value }))}
                        placeholder="Azure Tenant ID"
                        className="px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                                   placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                      />
                      <input
                        type="text"
                        value={distribution.sharepoint_client_id}
                        onChange={(e) => setDistribution((d) => ({ ...d, sharepoint_client_id: e.target.value }))}
                        placeholder="App Client ID"
                        className="px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                                   placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                      />
                    </div>
                    <input
                      type="password"
                      value={distribution.sharepoint_client_secret}
                      onChange={(e) => setDistribution((d) => ({ ...d, sharepoint_client_secret: e.target.value }))}
                      placeholder="App Client Secret"
                      className="w-full px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                                 placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                    />
                    <input
                      type="text"
                      value={distribution.sharepoint_folder}
                      onChange={(e) => setDistribution((d) => ({ ...d, sharepoint_folder: e.target.value }))}
                      placeholder="Folder path (default: KEEN Reports)"
                      className="w-full px-3 py-1.5 bg-transparent border border-theme-border rounded-lg text-xs
                                 placeholder:text-theme-text-muted/40 focus:outline-none focus:border-theme-text-muted"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <p className="text-xs text-red-400 font-mono bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-mono text-theme-text-muted hover:text-theme-text transition-colors"
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={loading || !form.company_name.trim()}
              className="flex items-center gap-2 px-5 py-2 bg-theme-text text-theme-bg text-xs font-mono
                         font-semibold rounded-lg hover:opacity-90 transition-opacity
                         disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  STARTING...
                </>
              ) : (
                'START PIPELINE →'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
