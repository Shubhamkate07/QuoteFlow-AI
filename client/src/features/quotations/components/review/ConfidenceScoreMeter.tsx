import React from 'react';
import { Sparkles, Info } from 'lucide-react';

interface ConfidenceScoreMeterProps {
  score?: number; // 0.0 - 1.0
  isApproved?: boolean;
}

export const ConfidenceScoreMeter: React.FC<ConfidenceScoreMeterProps> = ({
  score = 0.92,
  isApproved = false,
}) => {
  const percentage = Math.round(score * 100);

  const getConfidenceLevel = (val: number) => {
    if (val >= 95) return { label: 'High Confidence', color: 'text-emerald-700', bg: 'bg-emerald-500', pill: 'bg-emerald-50 border-emerald-200 text-emerald-800' };
    if (val >= 85) return { label: 'Medium Confidence', color: 'text-amber-700', bg: 'bg-amber-500', pill: 'bg-amber-50 border-amber-200 text-amber-800' };
    return { label: 'Needs Verification', color: 'text-rose-700', bg: 'bg-rose-500', pill: 'bg-rose-50 border-rose-200 text-rose-800' };
  };

  const level = getConfidenceLevel(percentage);

  return (
    <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-900">
              Gemini 2.0 AI Extraction Confidence
            </h4>
            <p className="text-[11px] text-slate-500">
              Multimodal document parsing and semantic schema alignment score
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {isApproved && (
            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              Approved
            </span>
          )}
          <div className="text-right">
            <span className="font-mono text-base font-bold text-slate-900">
              {percentage}%
            </span>
            <span className={`block text-[10px] font-semibold ${level.color}`}>
              {level.label}
            </span>
          </div>
          <div className="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${level.bg}`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Human-in-the-loop Advisory Banner */}
      <div className="p-3 bg-slate-50/80 rounded-lg border border-slate-200/80 flex items-start gap-2 text-[11px] text-slate-600 leading-relaxed">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-800 font-medium">Human Verification Notice: </strong>
          AI-extracted pricing and specification data should be visually reviewed against the original document. You can edit any field, adjust tax rates, or re-map line items before approving.
        </div>
      </div>
    </div>
  );
};
