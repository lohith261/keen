/**
 * CredentialsModal — lets users configure API keys / login credentials
 * for each connected integration.
 *
 * Opens as a full-screen modal with a sidebar list of systems on the left
 * and a credential form on the right. Each system shows a ✓ badge once
 * credentials have been saved for the current engagement.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  X, ChevronRight, CheckCircle2, Lock, Eye, EyeOff, Save,
  Loader2, AlertCircle, Trash2,
} from 'lucide-react';
import {
  credentialsApi,
  CREDENTIAL_SPECS,
  type SystemCredentialSpec,
} from '../../lib/apiClient';

interface Props {
  engagementId: string;
  onClose: () => void;
}

const CATEGORY_ORDER = ['CRM', 'ERP', 'Accounting', 'Marketing', 'Market Data', 'Intelligence', 'Export'];

function groupByCategory(specs: SystemCredentialSpec[]): Record<string, SystemCredentialSpec[]> {
  const groups: Record<string, SystemCredentialSpec[]> = {};
  for (const spec of specs) {
    if (!groups[spec.category]) groups[spec.category] = [];
    groups[spec.category].push(spec);
  }
  return groups;
}

export default function CredentialsModal({ engagementId, onClose }: Props) {
  const [configuredSystems, setConfiguredSystems] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<SystemCredentialSpec>(CREDENTIAL_SPECS[0]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load which systems already have credentials
  const refreshConfigured = useCallback(async () => {
    try {
      const { systems } = await credentialsApi.list(engagementId);
      setConfiguredSystems(new Set(systems));
    } catch {
      // Not critical — UI degrades gracefully
    }
  }, [engagementId]);

  useEffect(() => {
    refreshConfigured();
  }, [refreshConfigured]);

  // Clear form when switching systems
  const selectSystem = (spec: SystemCredentialSpec) => {
    setSelected(spec);
    setValues({});
    setShowSecret({});
    setSaveError(null);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    // Validate required fields
    for (const field of selected.fields) {
      if (field.required && !values[field.key]?.trim()) {
        setSaveError(`${field.label} is required`);
        return;
      }
    }

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      // Add company_name from URL or use placeholder
      const creds: Record<string, string> = {
        ...values,
      };
      await credentialsApi.store(engagementId, selected.system_name, selected.auth_type, creds);
      setSaveSuccess(true);
      setConfiguredSystems((prev) => new Set([...prev, selected.system_name]));
      setValues({});
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      let msg = 'Failed to save credentials';
      if (err instanceof Error) {
        // FastAPI 422 detail is an array of validation error objects — flatten to readable text
        try {
          const parsed = JSON.parse(err.message);
          if (Array.isArray(parsed)) {
            msg = parsed.map((e: { msg?: string; loc?: string[] }) =>
              [e.loc?.slice(-1)[0], e.msg].filter(Boolean).join(': ')
            ).join('; ');
          } else {
            msg = err.message;
          }
        } catch {
          msg = err.message;
        }
      }
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!configuredSystems.has(selected.system_name)) return;
    setDeleting(true);
    setSaveError(null);
    try {
      await credentialsApi.remove(engagementId, selected.system_name);
      setConfiguredSystems((prev) => {
        const next = new Set(prev);
        next.delete(selected.system_name);
        return next;
      });
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Failed to remove credentials');
    } finally {
      setDeleting(false);
    }
  };

  const grouped = groupByCategory(CREDENTIAL_SPECS);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div
        className="relative flex h-[90vh] w-[900px] max-w-[95vw] overflow-hidden rounded-2xl
                   border border-white/10 bg-[#0f1117] shadow-2xl"
      >
        {/* ── Close button ─────────────────────────────────────────────── */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-full p-1.5 text-white/50
                     transition hover:bg-white/10 hover:text-white"
        >
          <X size={18} />
        </button>

        {/* ── Left sidebar — system list ───────────────────────────────── */}
        <div className="flex h-full w-64 flex-shrink-0 flex-col overflow-y-auto border-r border-white/8
                        bg-[#080b10] py-6">
          <div className="px-5 pb-4">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-white/40">
              Integrations
            </h2>
          </div>

          {CATEGORY_ORDER.filter((cat) => grouped[cat]).map((category) => (
            <div key={category} className="mb-1">
              <div className="px-5 py-1.5">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25">
                  {category}
                </span>
              </div>
              {grouped[category].map((spec) => {
                const isConfigured = configuredSystems.has(spec.system_name);
                const isActive = selected.system_name === spec.system_name;
                return (
                  <button
                    key={spec.system_name}
                    onClick={() => selectSystem(spec)}
                    className={`flex w-full items-center gap-3 px-5 py-2.5 text-left text-sm
                               transition-colors
                               ${isActive
                                 ? 'bg-white/8 text-white'
                                 : 'text-white/60 hover:bg-white/5 hover:text-white/90'}`}
                  >
                    <span className="flex-1 truncate font-medium">{spec.display_name}</span>
                    {isConfigured ? (
                      <CheckCircle2 size={14} className="shrink-0 text-green-400" />
                    ) : (
                      <ChevronRight size={14} className="shrink-0 text-white/20" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* ── Right panel — credential form ────────────────────────────── */}
        <div className="flex flex-1 flex-col overflow-y-auto p-8">
          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">{selected.display_name}</h2>
              <p className="mt-1 text-sm text-white/40">
                {selected.auth_type} &middot; {selected.category}
              </p>
            </div>

            {configuredSystems.has(selected.system_name) && (
              <div className="flex items-center gap-2 rounded-full bg-green-500/15 px-3 py-1.5 text-xs
                              font-medium text-green-400">
                <CheckCircle2 size={12} />
                Credentials saved
              </div>
            )}
          </div>

          {/* Note about browser-based connectors */}
          {selected.auth_type === 'Browser Login' && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-blue-500/20
                            bg-blue-500/8 p-4 text-sm text-blue-300">
              <Lock size={16} className="mt-0.5 shrink-0" />
              <span>
                Credentials are encrypted with AES-256-GCM and used by our AI browser agent
                (TinyFish) to log in on your behalf. They are never stored in plaintext.
              </span>
            </div>
          )}

          {/* Fields */}
          <div className="space-y-4">
            {selected.fields.map((field) => {
              const isVisible = showSecret[field.key];
              return (
                <div key={field.key}>
                  <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-white/70">
                    {field.label}
                    {field.required && <span className="text-red-400">*</span>}
                  </label>
                  {/* Use textarea for long JSON fields, otherwise normal input */}
                  <div className="relative">
                    {field.placeholder.startsWith('{') ? (
                      <textarea
                        rows={5}
                        placeholder={field.placeholder}
                        value={values[field.key] ?? ''}
                        onChange={(e) =>
                          setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                        }
                        autoComplete="off"
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5
                                   text-sm text-white placeholder-white/25 outline-none resize-y
                                   font-mono transition focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30"
                      />
                    ) : (
                      <input
                        type={field.secret && !isVisible ? 'password' : 'text'}
                        placeholder={field.placeholder}
                        value={values[field.key] ?? ''}
                        onChange={(e) =>
                          setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                        }
                        autoComplete={field.secret ? 'new-password' : 'off'}
                        className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5
                                   pr-10 text-sm text-white placeholder-white/25 outline-none
                                   transition focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30"
                      />
                    )}
                    {field.secret && !field.placeholder.startsWith('{') && (
                      <button
                        type="button"
                        onClick={() =>
                          setShowSecret((prev) => ({ ...prev, [field.key]: !prev[field.key] }))
                        }
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30
                                   transition hover:text-white/60"
                      >
                        {isVisible ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Error / success banner */}
          {saveError && (
            <div className="mt-5 flex items-center gap-2 rounded-lg border border-red-500/30
                            bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertCircle size={15} className="shrink-0" />
              {saveError}
            </div>
          )}
          {saveSuccess && (
            <div className="mt-5 flex items-center gap-2 rounded-lg border border-green-500/30
                            bg-green-500/10 px-4 py-3 text-sm text-green-400">
              <CheckCircle2 size={15} className="shrink-0" />
              Credentials saved securely for this engagement.
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-8 flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm
                         font-medium text-white transition hover:bg-blue-500
                         disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {saving ? 'Saving…' : 'Save Credentials'}
            </button>

            {configuredSystems.has(selected.system_name) && (
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 rounded-lg border border-red-500/30
                           px-4 py-2.5 text-sm font-medium text-red-400 transition
                           hover:bg-red-500/10 disabled:opacity-60"
              >
                {deleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
                {deleting ? 'Removing…' : 'Remove'}
              </button>
            )}
          </div>

          {/* Security note */}
          <p className="mt-6 text-xs text-white/20">
            Credentials are encrypted before storage using AES-256-GCM.
            Only this engagement's pipeline can decrypt them.
            They are never logged or transmitted in plaintext.
          </p>
        </div>
      </div>
    </div>
  );
}
