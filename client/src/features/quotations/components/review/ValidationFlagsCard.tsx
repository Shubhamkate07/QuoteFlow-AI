import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../../components/ui/Card';
import { Badge } from '../../../../components/ui/Badge';
import type { ValidationFlag, ValidationSeverity } from '../../types/extraction';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
  Filter,
} from 'lucide-react';

interface ValidationFlagsCardProps {
  flags: ValidationFlag[];
  onSelectField?: (field: string) => void;
  selectedField?: string | null;
}

export const ValidationFlagsCard: React.FC<ValidationFlagsCardProps> = ({
  flags = [],
  onSelectField,
  selectedField,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<ValidationSeverity | 'ALL'>('ALL');

  const errorCount = flags.filter((f) => f.severity === 'ERROR').length;
  const warningCount = flags.filter((f) => f.severity === 'WARNING').length;
  const infoCount = flags.filter((f) => f.severity === 'INFO').length;

  const filteredFlags = filterSeverity === 'ALL'
    ? flags
    : flags.filter((f) => f.severity === filterSeverity);

  const getSeverityBadge = (severity: ValidationSeverity) => {
    switch (severity) {
      case 'ERROR':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            ERROR
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            WARNING
          </span>
        );
      case 'INFO':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <Info className="w-3 h-3 text-blue-600" />
            INFO
          </span>
        );
    }
  };

  return (
    <Card className="border-slate-200 shadow-2xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <div className={`p-1.5 rounded-lg ${errorCount > 0 ? 'bg-rose-50 text-rose-600' : warningCount > 0 ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'}`}>
              {errorCount > 0 ? (
                <AlertCircle className="w-4 h-4" />
              ) : warningCount > 0 ? (
                <AlertTriangle className="w-4 h-4" />
              ) : (
                <ShieldCheck className="w-4 h-4" />
              )}
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-slate-900">
                Deterministic Validation Flags
              </CardTitle>
              <p className="text-[11px] text-slate-500">
                Rule-based arithmetic, schema, and cross-field consistency checks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {errorCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800">
                {errorCount} Error{errorCount > 1 ? 's' : ''}
              </span>
            )}
            {warningCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">
                {warningCount} Warning{warningCount > 1 ? 's' : ''}
              </span>
            )}
            {infoCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-800">
                {infoCount} Info
              </span>
            )}
            {flags.length === 0 && (
              <Badge variant="success" size="sm">
                All Passed
              </Badge>
            )}
          </div>
        </div>

        {/* Filter controls if flags exist */}
        {flags.length > 0 && (
          <div className="flex items-center gap-1.5 pt-2 text-xs">
            <Filter className="w-3 h-3 text-slate-400 mr-1" />
            <span className="text-[11px] text-slate-500 font-medium">Filter:</span>
            {(['ALL', 'ERROR', 'WARNING', 'INFO'] as const).map((sev) => {
              const count = sev === 'ALL'
                ? flags.length
                : flags.filter((f) => f.severity === sev).length;
              if (sev !== 'ALL' && count === 0) return null;

              return (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setFilterSeverity(sev)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                    filterSeverity === sev
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {sev === 'ALL' ? 'All' : sev} ({count})
                </button>
              );
            })}
          </div>
        )}
      </CardHeader>

      <CardContent className="pt-3">
        {flags.length === 0 ? (
          <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg flex items-center gap-2.5 text-xs text-emerald-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="font-semibold">Deterministic Validation Clean:</span> No errors or arithmetic discrepancies detected. Grand totals, subtotals, tax calculations, and required fields are consistent.
            </div>
          </div>
        ) : filteredFlags.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500">
            No flags matching the selected severity filter.
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredFlags.map((flag, idx) => {
              const isSelected = selectedField && flag.field.includes(selectedField);
              const isClickable = Boolean(onSelectField);

              return (
                <div
                  key={`${flag.flag_type}-${flag.field}-${idx}`}
                  onClick={() => isClickable && onSelectField?.(flag.field)}
                  className={`p-3 rounded-lg border text-xs transition-all ${
                    flag.severity === 'ERROR'
                      ? 'bg-rose-50/50 border-rose-200'
                      : flag.severity === 'WARNING'
                      ? 'bg-amber-50/50 border-amber-200'
                      : 'bg-blue-50/50 border-blue-200'
                  } ${isSelected ? 'ring-2 ring-indigo-500' : ''} ${
                    isClickable ? 'cursor-pointer hover:shadow-xs' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getSeverityBadge(flag.severity)}
                      <span className="font-mono text-[11px] font-semibold text-slate-800 bg-white/80 px-1.5 py-0.5 rounded border border-slate-200">
                        {flag.field}
                      </span>
                      <span className="text-[10px] uppercase font-bold text-slate-500 font-mono">
                        {flag.flag_type}
                      </span>
                    </div>

                    {isClickable && (
                      <span className="text-[11px] text-indigo-600 font-medium flex items-center gap-0.5 hover:underline shrink-0">
                        Locate <ChevronRight className="w-3 h-3" />
                      </span>
                    )}
                  </div>

                  <p className="text-slate-700 leading-relaxed text-[11.5px] mt-1">
                    {flag.explanation}
                  </p>

                  {(flag.expected_value !== undefined || flag.actual_value !== undefined) && (
                    <div className="flex items-center gap-4 mt-2 pt-2 border-t border-slate-200/60 font-mono text-[11px]">
                      {flag.expected_value !== undefined && (
                        <div className="flex items-center gap-1">
                          <span className="text-slate-400 font-sans text-[10px] uppercase">Expected:</span>
                          <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            {String(flag.expected_value)}
                          </span>
                        </div>
                      )}
                      {flag.actual_value !== undefined && (
                        <div className="flex items-center gap-1">
                          <span className="text-slate-400 font-sans text-[10px] uppercase">Actual:</span>
                          <span className="font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                            {String(flag.actual_value)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
