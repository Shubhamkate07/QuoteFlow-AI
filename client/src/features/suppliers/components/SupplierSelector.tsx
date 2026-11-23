import React, { useState } from 'react';
import { useSuppliers } from '../context/SupplierContext';
import { Badge } from '../../../components/ui/Badge';
import { Search, Check } from 'lucide-react';

interface SupplierSelectorProps {
  selectedSupplierIds: string[];
  onChange: (ids: string[]) => void;
  categoryFilter?: string;
  label?: string;
  helperText?: string;
}

export const SupplierSelector: React.FC<SupplierSelectorProps> = ({
  selectedSupplierIds,
  onChange,
  categoryFilter,
  label = 'Select Invited Suppliers',
  helperText = 'Suppliers will receive the RFQ package to submit formal quotation bids.',
}) => {
  const { suppliers } = useSuppliers();
  const [search, setSearch] = useState('');

  const activeSuppliers = suppliers.filter((s) => s.status === 'active');

  const filteredSuppliers = activeSuppliers.filter((s) => {
    if (categoryFilter && categoryFilter !== 'all' && s.category !== categoryFilter) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        s.companyName.toLowerCase().includes(q) ||
        s.contactPerson.toLowerCase().includes(q) ||
        s.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const toggleSupplier = (id: string) => {
    if (selectedSupplierIds.includes(id)) {
      onChange(selectedSupplierIds.filter((item) => item !== id));
    } else {
      onChange([...selectedSupplierIds, id]);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-semibold text-slate-700">{label}</label>
        <span className="text-xs text-slate-500 font-medium">
          {selectedSupplierIds.length} selected
        </span>
      </div>

      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
          <Search className="w-3.5 h-3.5" />
        </div>
        <input
          type="text"
          placeholder="Filter suppliers by name or specialty..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800"
        />
      </div>

      {/* Supplier Selection List */}
      <div className="max-h-52 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 bg-white">
        {filteredSuppliers.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400">
            No active suppliers found matching this criteria.
          </div>
        ) : (
          filteredSuppliers.map((sup) => {
            const isSelected = selectedSupplierIds.includes(sup.id);
            return (
              <div
                key={sup.id}
                onClick={() => toggleSupplier(sup.id)}
                className={`p-2.5 flex items-center justify-between text-xs cursor-pointer transition-colors ${
                  isSelected ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                }`}
              >
                <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                  <div
                    className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                      isSelected
                        ? 'bg-slate-900 border-slate-900 text-white'
                        : 'border-slate-300 bg-white'
                    }`}
                  >
                    {isSelected && <Check className="w-3 h-3" />}
                  </div>

                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 truncate">
                      {sup.companyName}
                    </div>
                    <div className="text-[11px] text-slate-500 truncate">
                      {sup.contactPerson} • {sup.email}
                    </div>
                  </div>
                </div>

                <Badge variant="neutral" size="sm" className="text-[10px] shrink-0 capitalize">
                  {sup.category.replace('_', ' ')}
                </Badge>
              </div>
            );
          })
        )}
      </div>

      {helperText && <p className="text-[11px] text-slate-500">{helperText}</p>}
    </div>
  );
};
