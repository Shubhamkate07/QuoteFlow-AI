import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';

interface SupplierFilterBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  categoryFilter: string;
  onCategoryChange: (category: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
  countryFilter?: string;
  onCountryChange?: (country: string) => void;
  onReset: () => void;
}

export const SupplierFilterBar: React.FC<SupplierFilterBarProps> = ({
  searchQuery,
  onSearchChange,
  categoryFilter,
  onCategoryChange,
  statusFilter,
  onStatusChange,
  countryFilter = 'all',
  onCountryChange,
  onReset,
}) => {
  const hasActiveFilters =
    Boolean(searchQuery) ||
    categoryFilter !== 'all' ||
    statusFilter !== 'all' ||
    (countryFilter && countryFilter !== 'all');

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs mb-6 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 items-center">
        {/* Search */}
        <div className="lg:col-span-5 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Search suppliers by company name, contact person, email, or tax ID..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
          />
        </div>

        {/* Category */}
        <div className="lg:col-span-3">
          <Select
            value={categoryFilter}
            onChange={(e) => onCategoryChange(e.target.value)}
            options={[
              { value: 'all', label: 'All Categories' },
              { value: 'machining', label: 'CNC Machining & Tooling' },
              { value: 'fasteners', label: 'Hardware & Fasteners' },
              { value: 'sheet_metal', label: 'Sheet Metal Fabrication' },
              { value: 'plastics', label: 'Injection Molding & Polymers' },
              { value: 'electronics', label: 'Electronics & Harnesses' },
              { value: 'surface_treatment', label: 'Surface Treatment & Anodizing' },
              { value: 'raw_materials', label: 'Raw Bar & Plate Stock' },
              { value: 'other', label: 'Other Services' },
            ]}
          />
        </div>

        {/* Status */}
        <div className="lg:col-span-2">
          <Select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'active', label: 'Active Vendor' },
              { value: 'pending', label: 'Pending Onboarding' },
              { value: 'inactive', label: 'Inactive / Archived' },
            ]}
          />
        </div>

        {/* Country (if onCountryChange provided) */}
        {onCountryChange && (
          <div className="lg:col-span-1">
            <Select
              value={countryFilter}
              onChange={(e) => onCountryChange(e.target.value)}
              options={[
                { value: 'all', label: 'All' },
                { value: 'US', label: 'US' },
                { value: 'DE', label: 'DE' },
                { value: 'CN', label: 'CN' },
                { value: 'IN', label: 'IN' },
                { value: 'GB', label: 'GB' },
              ]}
            />
          </div>
        )}

        {/* Reset */}
        <div className={`flex justify-end ${onCountryChange ? 'lg:col-span-1' : 'lg:col-span-2'}`}>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-xs text-slate-500 hover:text-slate-800"
              title="Reset filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
