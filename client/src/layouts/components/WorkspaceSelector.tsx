import React, { useState, useRef, useEffect } from 'react';
import { Building2, Check, ChevronDown } from 'lucide-react';
import { useAuth } from '../../features/auth/context/AuthContext';

export const WorkspaceSelector: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { user, activeOrganization, switchOrganization } = useAuth();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const organizations = user?.organizations || [];
  const currentOrgName = activeOrganization?.name || 'Default Workspace';
  const currentOrgRole = activeOrganization?.role_display || 'Member';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer shadow-2xs"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <div className="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-700 shrink-0 border border-slate-200">
          <Building2 className="w-4 h-4 text-slate-600" />
        </div>
        <div className="hidden sm:block min-w-0 pr-1">
          <div className="text-xs font-semibold text-slate-800 truncate leading-tight">
            {currentOrgName}
          </div>
          <div className="text-[11px] text-slate-500 truncate leading-tight">
            {currentOrgRole}
          </div>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 rounded-xl bg-white border border-slate-200 shadow-xl py-1.5 z-50">
          <div className="px-3 py-2 border-b border-slate-100">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Organizations & Workspaces
            </span>
          </div>

          <div className="max-h-60 overflow-y-auto py-1">
            {organizations.length === 0 ? (
              <div className="px-3 py-2 text-xs text-slate-500 italic">No organizations available</div>
            ) : (
              organizations.map((org) => {
                const isSelected = org.id === activeOrganization?.id;
                return (
                  <button
                    key={org.id}
                    type="button"
                    onClick={() => {
                      switchOrganization(org.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-start space-x-3 px-3 py-2 text-left text-xs transition-colors cursor-pointer ${
                      isSelected ? 'bg-slate-50 text-slate-900' : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <div className="mt-0.5 w-6 h-6 rounded bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
                      <Building2 className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-slate-900 truncate">{org.name}</div>
                      <div className="text-[10px] text-emerald-600 font-medium mt-0.5">
                        {org.role_display}
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-1" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
