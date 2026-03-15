import { useState } from 'react';
import { X, Loader2, CheckCircle2 } from 'lucide-react';
import { leadsApi, type LeadInput } from '../lib/apiClient';

interface Props {
  onClose: () => void;
}

const AUM_RANGES = [
  { value: '', label: 'Select AUM range' },
  { value: '<500M', label: '< $500M' },
  { value: '500M-2B', label: '$500M – $2B' },
  { value: '2B-10B', label: '$2B – $10B' },
  { value: '>10B', label: '> $10B' },
];

export default function RequestAccessModal({ onClose }: Props) {
  const [form, setForm] = useState<LeadInput>({
    name: '',
    email: '',
    company: '',
    aum_range: '',
    message: '',
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await leadsApi.create({
        name: form.name.trim(),
        email: form.email.trim(),
        company: form.company?.trim() || undefined,
        aum_range: form.aum_range || undefined,
        message: form.message?.trim() || undefined,
      });
      setSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-theme-bg border border-theme-border rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-theme-border">
          <div>
            <h2 className="text-sm font-semibold tracking-wide">BOOK A DEMO</h2>
            <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
              We'll reach out to schedule a 30-min live session
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-theme-border transition-colors"
          >
            <X className="w-4 h-4 text-theme-text-muted" />
          </button>
        </div>

        {submitted ? (
          /* Success state */
          <div className="px-6 py-10 flex flex-col items-center text-center gap-4">
            <CheckCircle2 className="w-10 h-10 text-green-400" />
            <div>
              <p className="text-sm font-semibold">You're on the list</p>
              <p className="text-[12px] text-theme-text-muted mt-1 max-w-xs">
                We'll reach out within 24 hours to schedule a live walkthrough. In the meantime, explore the demo dashboard.
              </p>
            </div>
            <button
              onClick={onClose}
              className="mt-2 px-5 py-2 bg-theme-text text-theme-bg text-xs font-mono font-semibold rounded-lg hover:opacity-90 transition-opacity"
            >
              CLOSE
            </button>
          </div>
        ) : (
          /* Form */
          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Jane Smith"
                  className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                             placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                             transition-colors"
                />
              </div>
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="jane@firm.com"
                  className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                             placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                             transition-colors"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                  Firm / Company
                </label>
                <input
                  type="text"
                  value={form.company}
                  onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                  placeholder="Accel Partners"
                  className="w-full px-3 py-2 bg-transparent border border-theme-border rounded-lg text-sm
                             placeholder:text-theme-text-muted/50 focus:outline-none focus:border-theme-text-muted
                             transition-colors"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                  AUM Range
                </label>
                <select
                  value={form.aum_range}
                  onChange={(e) => setForm((f) => ({ ...f, aum_range: e.target.value }))}
                  className="w-full px-3 py-2 bg-theme-bg border border-theme-border rounded-lg text-sm
                             focus:outline-none focus:border-theme-text-muted transition-colors"
                >
                  {AUM_RANGES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-theme-text-muted mb-1.5 uppercase tracking-wider">
                Message
              </label>
              <textarea
                rows={3}
                value={form.message}
                onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                placeholder="Tell us about your use case or timeline"
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
                disabled={loading || !form.name.trim() || !form.email.trim()}
                className="flex items-center gap-2 px-5 py-2 bg-orange-600 hover:bg-orange-500 text-white text-xs font-mono
                           font-semibold rounded-lg transition-colors
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    SUBMITTING...
                  </>
                ) : (
                  'SUBMIT REQUEST →'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
