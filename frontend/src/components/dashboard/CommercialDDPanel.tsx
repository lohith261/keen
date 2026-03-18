import { useEffect, useState } from 'react';
import {
  MessageSquare, Plus, Trash2, ChevronDown, ChevronUp,
  Loader2, Users, TrendingUp,
} from 'lucide-react';
import {
  primaryResearchApi,
  type PrimaryResearchRecord,
  type ResearchSummary,
} from '../../lib/apiClient';

interface Props {
  engagementId: string;
  companyName: string;
  readOnly?: boolean;
}

type FilterType = 'all' | 'customer_interview' | 'channel_check' | 'win_loss' | 'market_sizing';

const TYPE_LABELS: Record<string, string> = {
  customer_interview: 'INTERVIEW',
  channel_check: 'CHANNEL',
  win_loss: 'WIN-LOSS',
  market_sizing: 'MARKET',
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-green-400 border-green-500/40 bg-green-500/10',
  negative: 'text-red-400 border-red-500/40 bg-red-500/10',
  neutral: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
  mixed: 'text-purple-400 border-purple-500/40 bg-purple-500/10',
};

export default function CommercialDDPanel({ engagementId, companyName, readOnly }: Props) {
  const [records, setRecords] = useState<PrimaryResearchRecord[]>([]);
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [form, setForm] = useState({
    type: 'customer_interview' as PrimaryResearchRecord['type'],
    company_name: '',
    contact_name: '',
    contact_role: '',
    notes: '',
  });

  async function load() {
    setLoading(true);
    try {
      const [recs, summ] = await Promise.all([
        primaryResearchApi.list(engagementId, filter === 'all' ? undefined : filter),
        primaryResearchApi.summary(engagementId),
      ]);
      setRecords(recs);
      setSummary(summ);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engagementId, filter]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await primaryResearchApi.create(engagementId, {
        type: form.type,
        company_name: form.company_name || companyName,
        contact_name: form.contact_name || null,
        contact_role: form.contact_role || null,
        notes: form.notes || null,
      });
      setForm({ type: 'customer_interview', company_name: '', contact_name: '', contact_role: '', notes: '' });
      setShowForm(false);
      await load();
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(recordId: string) {
    setDeletingId(recordId);
    try {
      await primaryResearchApi.delete(engagementId, recordId);
      await load();
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  }

  const filterTabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'ALL' },
    { key: 'customer_interview', label: 'INTERVIEWS' },
    { key: 'channel_check', label: 'CHANNEL' },
    { key: 'win_loss', label: 'WIN-LOSS' },
    { key: 'market_sizing', label: 'MARKET' },
  ];

  return (
    <div className="space-y-4 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-indigo-400" />
          <span className="text-[11px] text-theme-text-muted uppercase tracking-widest">
            Commercial DD — Primary Research
          </span>
        </div>
        {!readOnly && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono
                       border border-indigo-500/40 text-indigo-400 rounded hover:bg-indigo-500/10 transition-colors"
          >
            <Plus className="w-3 h-3" />
            ADD RECORD
          </button>
        )}
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="border border-theme-border rounded-lg p-3 bg-theme-surface/40">
            <div className="text-[10px] text-theme-text-muted mb-1">TOTAL RECORDS</div>
            <div className="text-xl text-theme-text">{summary.total}</div>
          </div>
          <div className="border border-theme-border rounded-lg p-3 bg-theme-surface/40">
            <div className="flex items-center gap-1 text-[10px] text-theme-text-muted mb-1">
              <TrendingUp className="w-3 h-3" /> POSITIVE
            </div>
            <div className="text-xl text-green-400">{summary.sentiment_distribution?.positive ?? 0}</div>
          </div>
          <div className="border border-theme-border rounded-lg p-3 bg-theme-surface/40">
            <div className="flex items-center gap-1 text-[10px] text-theme-text-muted mb-1">
              <Users className="w-3 h-3" /> COMPANIES
            </div>
            <div className="text-xl text-theme-text">{summary.companies_covered?.length ?? 0}</div>
          </div>
          <div className="border border-theme-border rounded-lg p-3 bg-theme-surface/40 col-span-2 md:col-span-1">
            <div className="text-[10px] text-theme-text-muted mb-1">TOP THEMES</div>
            <div className="text-[10px] text-theme-text leading-relaxed">
              {(summary.top_themes ?? []).slice(0, 3).join(' · ') || '—'}
            </div>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1 border border-theme-border rounded-lg p-0.5 flex-wrap">
        {filterTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-3 py-1 text-[10px] font-mono rounded-md transition-colors ${
              filter === tab.key
                ? 'bg-theme-text text-theme-bg font-semibold'
                : 'text-theme-text-muted hover:text-theme-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Add record form */}
      {showForm && !readOnly && (
        <form
          onSubmit={(e) => { void handleCreate(e); }}
          className="border border-indigo-500/30 rounded-lg p-4 bg-indigo-500/5 space-y-3"
        >
          <div className="text-[10px] text-indigo-400 uppercase tracking-widest mb-2">New Research Record</div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-theme-text-muted">TYPE</label>
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as PrimaryResearchRecord['type'] }))}
                className="mt-1 w-full bg-theme-bg border border-theme-border rounded px-2 py-1.5
                           text-[11px] text-theme-text focus:outline-none focus:border-indigo-500"
              >
                <option value="customer_interview">Customer Interview</option>
                <option value="channel_check">Channel Check</option>
                <option value="win_loss">Win/Loss</option>
                <option value="market_sizing">Market Sizing</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-theme-text-muted">COMPANY</label>
              <input
                type="text"
                value={form.company_name}
                placeholder={companyName}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className="mt-1 w-full bg-theme-bg border border-theme-border rounded px-2 py-1.5
                           text-[11px] text-theme-text placeholder:text-theme-text-muted/50
                           focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-theme-text-muted">CONTACT NAME</label>
              <input
                type="text"
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                className="mt-1 w-full bg-theme-bg border border-theme-border rounded px-2 py-1.5
                           text-[11px] text-theme-text placeholder:text-theme-text-muted/50
                           focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-theme-text-muted">CONTACT ROLE</label>
              <input
                type="text"
                value={form.contact_role}
                onChange={(e) => setForm((f) => ({ ...f, contact_role: e.target.value }))}
                className="mt-1 w-full bg-theme-bg border border-theme-border rounded px-2 py-1.5
                           text-[11px] text-theme-text placeholder:text-theme-text-muted/50
                           focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] text-theme-text-muted">NOTES</label>
            <textarea
              value={form.notes}
              rows={3}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              className="mt-1 w-full bg-theme-bg border border-theme-border rounded px-2 py-1.5
                         text-[11px] text-theme-text placeholder:text-theme-text-muted/50
                         focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono
                         bg-indigo-500/20 border border-indigo-500/40 text-indigo-400
                         rounded hover:bg-indigo-500/30 transition-colors disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
              SAVE
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 text-[10px] font-mono text-theme-text-muted
                         hover:text-theme-text transition-colors"
            >
              CANCEL
            </button>
          </div>
        </form>
      )}

      {/* Records list */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-4 h-4 animate-spin text-theme-text-muted" />
        </div>
      ) : records.length === 0 ? (
        <div className="text-center py-8 text-[11px] text-theme-text-muted">
          No research records yet.
        </div>
      ) : (
        <div className="space-y-2">
          {records.map((rec) => {
            const isExpanded = expandedId === rec.id;
            const sentimentColor = SENTIMENT_COLORS[rec.sentiment ?? ''] ?? 'text-theme-text-muted border-theme-border bg-theme-surface/20';
            return (
              <div key={rec.id} className="border border-theme-border rounded-lg bg-theme-surface/40">
                <div
                  className="flex items-center gap-3 p-3 cursor-pointer hover:bg-theme-surface/60 transition-colors rounded-lg"
                  onClick={() => setExpandedId(isExpanded ? null : rec.id)}
                >
                  <span className="text-[9px] px-1.5 py-0.5 border border-theme-border rounded text-theme-text-muted">
                    {TYPE_LABELS[rec.type] ?? rec.type}
                  </span>
                  <span className="flex-1 text-[11px] text-theme-text truncate">
                    {rec.company_name}
                    {rec.contact_name ? ` · ${rec.contact_name}` : ''}
                    {rec.contact_role ? ` (${rec.contact_role})` : ''}
                  </span>
                  {rec.sentiment && (
                    <span className={`text-[9px] px-1.5 py-0.5 border rounded ${sentimentColor}`}>
                      {rec.sentiment.toUpperCase()}
                    </span>
                  )}
                  {rec.interview_date && (
                    <span className="text-[10px] text-theme-text-muted hidden sm:block">
                      {rec.interview_date.slice(0, 10)}
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    {!readOnly && (
                      <button
                        onClick={(e) => { e.stopPropagation(); void handleDelete(rec.id); }}
                        disabled={deletingId === rec.id}
                        className="p-1 text-theme-text-muted hover:text-red-400 transition-colors"
                      >
                        {deletingId === rec.id
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : <Trash2 className="w-3 h-3" />}
                      </button>
                    )}
                    {isExpanded
                      ? <ChevronUp className="w-3.5 h-3.5 text-theme-text-muted" />
                      : <ChevronDown className="w-3.5 h-3.5 text-theme-text-muted" />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-3 pb-3 space-y-2 border-t border-theme-border/50 pt-2">
                    {rec.notes && (
                      <div>
                        <div className="text-[10px] text-theme-text-muted mb-1">NOTES</div>
                        <p className="text-[11px] text-theme-text leading-relaxed">{rec.notes}</p>
                      </div>
                    )}
                    {rec.key_themes?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-theme-text-muted mb-1">KEY THEMES</div>
                        <div className="flex flex-wrap gap-1">
                          {rec.key_themes.map((t) => (
                            <span key={t} className="text-[9px] px-1.5 py-0.5 border border-theme-border rounded text-theme-text-muted">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {rec.action_items?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-theme-text-muted mb-1">ACTION ITEMS</div>
                        <ul className="space-y-0.5">
                          {rec.action_items.map((item, i) => (
                            <li key={i} className="text-[11px] text-theme-text flex items-start gap-1.5">
                              <span className="text-indigo-400 mt-px">›</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
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
