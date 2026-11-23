import React from 'react';
import {
  FileText,
  Calculator,
  Sparkles,
  AlertTriangle,
  UserCheck,
} from 'lucide-react';
import type { DataOriginType } from '../types';

interface DataOriginBadgeProps {
  type: DataOriginType;
  label?: string;
  size?: 'xs' | 'sm';
  showIcon?: boolean;
  className?: string;
}

/**
 * Visual badge clearly distinguishing:
 * - Actual extracted data
 * - Calculated values
 * - AI interpretations
 * - Risk flags
 * - User decisions
 */
export const DataOriginBadge: React.FC<DataOriginBadgeProps> = ({
  type,
  label,
  size = 'xs',
  showIcon = true,
  className = '',
}) => {
  const config = {
    extracted: {
      defaultLabel: 'Actual Extracted',
      badgeClass: 'bg-slate-100 text-slate-700 border-slate-300/80',
      icon: <FileText className="w-3 h-3 text-slate-500" />,
      title: 'Directly extracted from supplier quote document without modification',
    },
    calculated: {
      defaultLabel: 'Calculated',
      badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200/90',
      icon: <Calculator className="w-3 h-3 text-indigo-600" />,
      title: 'Deterministically computed through arithmetic and objective formulas',
    },
    ai: {
      defaultLabel: 'AI Interpretation',
      badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
      icon: <Sparkles className="w-3 h-3 text-purple-600" />,
      title: 'Interpreted via AI semantic specification matching with confidence score',
    },
    risk: {
      defaultLabel: 'Risk Flag',
      badgeClass: 'bg-amber-50 text-amber-800 border-amber-300/80',
      icon: <AlertTriangle className="w-3 h-3 text-amber-600" />,
      title: 'Flagged by deterministic commercial and contract risk rules',
    },
    decision: {
      defaultLabel: 'User Decision',
      badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-300/80',
      icon: <UserCheck className="w-3 h-3 text-emerald-600" />,
      title: 'Approved or customized by human procurement officer',
    },
  }[type];

  const sizeClass =
    size === 'xs'
      ? 'text-[9px] px-1.5 py-0.5 tracking-tight'
      : 'text-[10px] px-2 py-0.5';

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-md border font-sans select-none ${config.badgeClass} ${sizeClass} ${className}`}
      title={config.title}
    >
      {showIcon && config.icon}
      <span>{label || config.defaultLabel}</span>
    </span>
  );
};
