import React from 'react';
import type { QuotationStatus } from '../types';
import {
  UploadCloud,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
} from 'lucide-react';

interface QuotationStatusBadgeProps {
  status: QuotationStatus;
  progress?: number;
  className?: string;
  size?: 'sm' | 'md';
}

export const QuotationStatusBadge: React.FC<QuotationStatusBadgeProps> = ({
  status,
  progress,
  className = '',
  size = 'md',
}) => {
  const sizeClasses = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5';

  switch (status) {
    case 'uploaded':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses} ${className}`}
        >
          <UploadCloud className={`${iconSize} text-slate-500`} />
          <span>Uploaded (Queued)</span>
        </span>
      );

    case 'processing':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-200 ${sizeClasses} ${className}`}
        >
          <Loader2 className={`${iconSize} animate-spin text-sky-600`} />
          <span>
            {progress !== undefined && progress > 0
              ? `Processing (${progress}%)`
              : 'Processing AI...'}
          </span>
        </span>
      );

    case 'completed':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 ${sizeClasses} ${className}`}
        >
          <CheckCircle2 className={`${iconSize} text-emerald-600`} />
          <span>Completed</span>
        </span>
      );

    case 'needs_review':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-50 text-amber-800 border border-amber-200 ${sizeClasses} ${className}`}
        >
          <AlertTriangle className={`${iconSize} text-amber-600`} />
          <span>Needs Review</span>
        </span>
      );

    case 'failed':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-rose-50 text-rose-700 border border-rose-200 ${sizeClasses} ${className}`}
        >
          <AlertCircle className={`${iconSize} text-rose-600`} />
          <span>Extraction Failed</span>
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses} ${className}`}
        >
          <span>{status}</span>
        </span>
      );
  }
};
