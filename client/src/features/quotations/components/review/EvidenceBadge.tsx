import React, { useState } from 'react';
import type { FieldEvidence } from '../../types/extraction';
import { FileSearch, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

interface EvidenceBadgeProps {
  evidence?: FieldEvidence;
  fieldName?: string;
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({ evidence, fieldName }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!evidence || (!evidence.source_text && !evidence.page_number && evidence.confidence_level === undefined)) {
    return null;
  }

  const confidencePct = evidence.confidence_level !== undefined && evidence.confidence_level !== null
    ? Math.round(Number(evidence.confidence_level) * 100)
    : null;

  const getConfidenceStyle = (pct: number) => {
    if (pct >= 95) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (pct >= 80) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-rose-700 bg-rose-50 border-rose-200';
  };

  return (
    <div className="inline-block relative">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-medium border bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 transition-colors"
        title={`Click to view extraction evidence citation${fieldName ? ` for ${fieldName}` : ''}`}
      >
        <FileSearch className="w-3 h-3 text-indigo-500" />
        {evidence.page_number && (
          <span className="font-mono text-slate-700 font-semibold">p.{evidence.page_number}</span>
        )}
        {confidencePct !== null && (
          <span className={`px-1 rounded font-mono font-bold ${getConfidenceStyle(confidencePct)}`}>
            {confidencePct}%
          </span>
        )}
        {isExpanded ? <ChevronUp className="w-2.5 h-2.5 text-slate-400" /> : <ChevronDown className="w-2.5 h-2.5 text-slate-400" />}
      </button>

      {isExpanded && (
        <div className="absolute left-0 top-full mt-1 z-30 w-72 p-3 bg-white rounded-xl border border-slate-200 shadow-lg text-xs space-y-2 animate-in fade-in slide-in-from-top-1">
          <div className="flex items-center justify-between pb-1 border-b border-slate-100">
            <span className="font-semibold text-slate-800 text-[11px] flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-500" />
              Source Evidence Citation
            </span>
            {confidencePct !== null && (
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${getConfidenceStyle(confidencePct)}`}>
                {confidencePct}% confidence
              </span>
            )}
          </div>

          {evidence.page_number && (
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Document Page:</span>
              <span className="font-mono font-bold text-slate-800">Page {evidence.page_number}</span>
            </div>
          )}

          {evidence.source_text && (
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-0.5">
                Exact Verbatim Text:
              </span>
              <blockquote className="p-2 bg-slate-50 border-l-2 border-indigo-400 rounded text-[11px] font-mono text-slate-700 leading-snug break-words">
                "{evidence.source_text}"
              </blockquote>
            </div>
          )}

          {evidence.extracted_value !== undefined && evidence.extracted_value !== null && (
            <div className="text-[10px] text-slate-500 flex justify-between pt-1 border-t border-slate-100">
              <span>Parsed Value:</span>
              <span className="font-mono font-medium text-slate-800">{String(evidence.extracted_value)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
