import React from 'react';
import { Card, CardContent } from '../../../components/ui/Card';
import { Select } from '../../../components/ui/Select';
import { Button } from '../../../components/ui/Button';
import type {
  ComparisonFilterState,
  ComparisonSortOption,
  ComparisonViewTab,
  ComparisonSupplierBid,
} from '../types';
import type { Rfq } from '../../rfq/types';
import { DataOriginBadge } from './DataOriginBadge';
import {
  ArrowUpDown,
  RotateCcw,
  CheckSquare,
  Square,
  Layers,
  Sliders,
  RefreshCw,
  LayoutGrid,
  DollarSign,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

interface ComparisonFilterBarProps {
  rfqs: Rfq[];
  selectedRfqId: string;
  onSelectRfq: (rfqId: string) => void;
  filterState: ComparisonFilterState;
  onFilterChange: (updates: Partial<ComparisonFilterState>) => void;
  availableBids: ComparisonSupplierBid[];
  onResetFilters: () => void;
  onOpenCustomWeights: () => void;
  onRegenerate: () => void;
  isRegenerating?: boolean;
  activeTab: ComparisonViewTab;
  onTabChange: (tab: ComparisonViewTab) => void;
}

export const ComparisonFilterBar: React.FC<ComparisonFilterBarProps> = ({
  rfqs,
  selectedRfqId,
  onSelectRfq,
  filterState,
  onFilterChange,
  availableBids,
  onResetFilters,
  onOpenCustomWeights,
  onRegenerate,
  isRegenerating = false,
  activeTab,
  onTabChange,
}) => {
  const toggleSupplierVisibility = (supplierId: string) => {
    const isVisible = filterState.visibleSupplierIds.includes(supplierId);
    if (isVisible) {
      if (filterState.visibleSupplierIds.length > 1) {
        onFilterChange({
          visibleSupplierIds: filterState.visibleSupplierIds.filter((id) => id !== supplierId),
        });
      }
    } else {
      onFilterChange({
        visibleSupplierIds: [...filterState.visibleSupplierIds, supplierId],
      });
    }
  };

  return (
    <Card className="mb-6 shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-3 gap-3">
          <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg text-xs font-medium">
            <button
              type="button"
              onClick={() => onTabChange('matrix')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'matrix'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Side-by-Side Matrix</span>
            </button>

            <button
              type="button"
              onClick={() => onTabChange('price')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'price'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <DollarSign className="w-3.5 h-3.5" />
              <span>Price & Cherry-Pick</span>
            </button>

            <button
              type="button"
              onClick={() => onTabChange('specs')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'specs'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Specification Compliance</span>
            </button>

            <button
              type="button"
              onClick={() => onTabChange('risk')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'risk'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Risk & Audit Flags</span>
            </button>
          </div>

          {/* Action Buttons: Scoring Weights & Regenerate */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenCustomWeights}
              leftIcon={<Sliders className="w-3.5 h-3.5 text-indigo-600" />}
              className="text-xs"
            >
              Scoring Weights
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onRegenerate}
              isLoading={isRegenerating}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />}
              className="text-xs"
              title="Force recomputation of comparison using latest approved quotation data"
            >
              Regenerate
            </Button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5 items-end">
          {/* RFQ Selector */}
          <div className="md:col-span-4">
            <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>Select Procurement RFQ Package</span>
            </label>
            <Select
              value={selectedRfqId}
              onChange={(e) => onSelectRfq(e.target.value)}
              options={rfqs.map((rfq) => ({
                value: rfq.id,
                label: `${rfq.rfqNumber}: ${rfq.title}`,
              }))}
            />
          </div>

          {/* Sort By Dropdown */}
          <div className="md:col-span-3">
            <label className="block text-xs font-medium text-slate-700 mb-1 flex items-center gap-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <span>Sort Supplier Columns</span>
            </label>
            <Select
              value={filterState.sortBy}
              onChange={(e) =>
                onFilterChange({ sortBy: e.target.value as ComparisonSortOption })
              }
              options={[
                { value: 'highest_score', label: 'Highest Evaluated Score' },
                { value: 'lowest_price', label: 'Lowest Total Quoted Price' },
                { value: 'highest_spec', label: 'Highest Spec Match %' },
                { value: 'shortest_lead', label: 'Shortest Delivery Lead Time' },
              ]}
            />
          </div>

          {/* Min Spec Match Filter */}
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Min Spec Match
            </label>
            <Select
              value={filterState.minSpecMatch.toString()}
              onChange={(e) => onFilterChange({ minSpecMatch: Number(e.target.value) })}
              options={[
                { value: '0', label: 'All Bids (0%+)' },
                { value: '85', label: '≥ 85% Match' },
                { value: '90', label: '≥ 90% Match' },
                { value: '95', label: '≥ 95% Match' },
                { value: '100', label: '100% Strict Match' },
              ]}
            />
          </div>

          {/* Risk Level Filter */}
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Risk Profile
            </label>
            <Select
              value={filterState.riskFilter}
              onChange={(e) =>
                onFilterChange({
                  riskFilter: e.target.value as 'all' | 'low_risk_only',
                })
              }
              options={[
                { value: 'all', label: 'All Risk Profiles' },
                { value: 'low_risk_only', label: 'Low Risk Only' },
              ]}
            />
          </div>

          {/* Reset Filters */}
          <div className="md:col-span-1">
            <Button
              variant="outline"
              size="sm"
              onClick={onResetFilters}
              className="w-full py-2 text-xs"
              title="Reset all comparison filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Visible Supplier Checkbox Pills & Approved Only Toggle */}
        <div className="pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-500 font-medium text-[11px] mr-1">
              Visible Suppliers ({filterState.visibleSupplierIds.length}/{availableBids.length}):
            </span>
            {availableBids.map((b) => {
              const isChecked = filterState.visibleSupplierIds.includes(b.supplierId);
              return (
                <button
                  key={b.supplierId}
                  type="button"
                  onClick={() => toggleSupplierVisibility(b.supplierId)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                    isChecked
                      ? 'bg-indigo-50 border-indigo-200 text-indigo-900'
                      : 'bg-slate-50 border-slate-200 text-slate-400 hover:bg-slate-100'
                  }`}
                >
                  {isChecked ? (
                    <CheckSquare className="w-3.5 h-3.5 text-indigo-600" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span>{b.supplierName}</span>
                </button>
              );
            })}
          </div>

          {/* Approved Only Policy Switch */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filterState.approvedOnly}
              onChange={(e) => onFilterChange({ approvedOnly: e.target.checked })}
              className="w-3.5 h-3.5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span className="text-xs font-medium text-slate-700">
              Approved Quotations Only
            </span>
            <DataOriginBadge type="decision" size="xs" label="Verified" />
          </label>
        </div>
      </CardContent>
    </Card>
  );
};
