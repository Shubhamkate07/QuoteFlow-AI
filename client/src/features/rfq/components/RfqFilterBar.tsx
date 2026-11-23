import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';

interface RfqFilterBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
  dateFilter: string;
  onDateChange: (dateFilter: string) => void;
  currencyFilter: string;
  onCurrencyChange: (currency: string) => void;
  onReset: () => void;
}

export const RfqFilterBar: React.FC<RfqFilterBarProps> = ({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  dateFilter,
  onDateChange,
  currencyFilter,
  onCurrencyChange,
  onReset,
}) => {
  const hasActiveFilters =
    Boolean(searchQuery) ||
    statusFilter !== 'all' ||
    dateFilter !== 'all' ||
    currencyFilter !== 'all';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs mb-6 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 items-center">
        {/* Search input */}
        <div className="lg:col-span-5 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Search by title, part name, or RFQ number (e.g. RFQ-2026-0042)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
          />
        </div>

        {/* Status Filter */}
        <div className="lg:col-span-2">
          <Select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'draft', label: 'Draft' },
              { value: 'open', label: 'Open for Bids' },
              { value: 'under_review', label: 'Under Review' },
              { value: 'awarded', label: 'Awarded' },
              { value: 'closed', label: 'Closed' },
            ]}
          />
        </div>

        {/* Date Filter */}
        <div className="lg:col-span-2">
          <Select
            value={dateFilter}
            onChange={(e) => onDateChange(e.target.value)}
            options={[
              { value: 'all', label: 'All Deadlines' },
              { value: 'next_14', label: 'Next 14 Days' },
              { value: 'next_30', label: 'Next 30 Days' },
              { value: 'next_60', label: 'Next 60 Days' },
              { value: '2027', label: 'Year 2027' },
            ]}
          />
        </div>

        {/* Currency Filter */}
        <div className="lg:col-span-2">
          <Select
            value={currencyFilter}
            onChange={(e) => onCurrencyChange(e.target.value)}
            options={[
              { value: 'all', label: 'All Currencies' },
              { value: 'USD', label: 'USD ($)' },
              { value: 'EUR', label: 'EUR (€)' },
              { value: 'GBP', label: 'GBP (£)' },
            ]}
          />
        </div>

        {/* Reset Filter Button */}
        <div className="lg:col-span-1 flex justify-end">
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-xs text-slate-500 hover:text-slate-800"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
