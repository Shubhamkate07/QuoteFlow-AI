import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import { Button } from '../ui/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('QuoteFlow UI Uncaught Error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
            <div className="inline-flex p-3 bg-rose-500/10 text-rose-400 rounded-xl mb-4">
              <AlertOctagon className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-sm text-slate-400 mb-6">
              An unexpected application error occurred while rendering this view.
            </p>
            {this.state.error && (
              <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-rose-400 text-left mb-6 overflow-auto max-h-32">
                {this.state.error.message}
              </div>
            )}
            <Button onClick={this.handleReset} className="w-full gap-2">
              <RotateCcw className="w-4 h-4" />
              <span>Reload Application</span>
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
