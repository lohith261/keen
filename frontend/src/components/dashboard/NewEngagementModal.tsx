import { useState } from 'react';
import { X, FlaskConical, Radio, Loader2 } from 'lucide-react';
import { engagementsApi, type Engagement } from '../../lib/apiClient';
import { useDemoMode } from '../../context/DemoModeContext';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const engagement = await engagementsApi.create({
        company_name: form.company_name.trim(),
        pe_firm: form.pe_firm.trim() || undefined,
        deal_size: form.deal_size.trim() || undefined,
        notes: form.notes.trim() || undefined,
        config: { engagement_type: form.engagement_type },
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
          <div>
            <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
              Target Company *
            </label>
            <input
              type="text"
              required
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              placeholder="e.g. Zendesk Inc."
              className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                         placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                         transition-colors"
            />
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
