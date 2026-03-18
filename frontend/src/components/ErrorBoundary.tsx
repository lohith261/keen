import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : String(error);
    return { hasError: true, message };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-theme-bg text-theme-text flex items-center justify-center p-8">
          <div className="max-w-md w-full border border-red-500/30 rounded-xl p-6 space-y-4 bg-red-500/5">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <h2 className="text-sm font-semibold">Something went wrong</h2>
            </div>
            <p className="text-[11px] font-mono text-theme-text-muted leading-relaxed break-words">
              {this.state.message}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono
                         border border-theme-border rounded-lg hover:bg-theme-border/30 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
