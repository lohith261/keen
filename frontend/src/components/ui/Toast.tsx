/**
 * Toast notification system.
 *
 * Usage:
 *   const { addToast } = useToast();
 *   addToast({ type: 'success', message: 'Exported!', action: { label: 'Open', onClick: () => window.open(url) } });
 *
 * Wrap your app (or Dashboard) in <ToastProvider>.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  detail?: string;
  action?: ToastAction;
  duration?: number; // ms; 0 = persistent
}

interface ToastContextValue {
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

// ── Config ────────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  ToastType,
  { icon: React.ElementType; color: string; border: string; bg: string }
> = {
  success: {
    icon: CheckCircle,
    color: 'text-green-400',
    border: 'border-green-500/30',
    bg: 'bg-green-500/8',
  },
  error: {
    icon: XCircle,
    color: 'text-red-400',
    border: 'border-red-500/30',
    bg: 'bg-red-500/8',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-400',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/8',
  },
  info: {
    icon: Info,
    color: 'text-blue-400',
    border: 'border-blue-500/30',
    bg: 'bg-blue-500/8',
  },
};

// ── Single Toast Item ─────────────────────────────────────────────────────────

function ToastItem({
  toast,
  onRemove,
}: {
  toast: Toast;
  onRemove: (id: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  const cfg = TYPE_CONFIG[toast.type];
  const Icon = cfg.icon;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Slide in
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  // Auto-dismiss
  useEffect(() => {
    const duration = toast.duration ?? 5000;
    if (duration === 0) return;
    timerRef.current = setTimeout(() => dismiss(), duration);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function dismiss() {
    setVisible(false);
    setTimeout(() => onRemove(toast.id), 300);
  }

  return (
    <div
      className={`
        flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-md
        transition-all duration-300 max-w-sm w-full
        ${cfg.bg} ${cfg.border}
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
    >
      <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${cfg.color}`} />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-semibold text-theme-text leading-snug">
          {toast.message}
        </p>
        {toast.detail && (
          <p className="text-[10px] font-mono text-theme-text-muted mt-0.5 leading-snug">
            {toast.detail}
          </p>
        )}
        {toast.action && (
          <button
            onClick={() => { toast.action!.onClick(); dismiss(); }}
            className={`mt-1.5 text-[10px] font-mono font-semibold underline underline-offset-2 ${cfg.color} hover:opacity-70 transition-opacity`}
          >
            {toast.action.label} →
          </button>
        )}
      </div>
      <button
        onClick={dismiss}
        className="flex-shrink-0 text-theme-text-muted hover:text-theme-text transition-colors mt-0.5"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// ── Provider + Container ──────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const addToast = useCallback((t: Omit<Toast, 'id'>): string => {
    const id = `toast-${++counter.current}`;
    setToasts((prev) => [...prev, { ...t, id }]);
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}

      {/* Toast container — bottom-right */}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onRemove={removeToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
