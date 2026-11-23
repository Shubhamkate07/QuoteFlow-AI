import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Users,
  FileCheck2,
  GitCompare,
  BarChart3,
  Settings,
  Layers,
  Sparkles,
} from 'lucide-react';
import { ROUTES } from '../../routes/paths';

export interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeVariant?: 'neutral' | 'warning' | 'success';
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: 'RFQs', path: ROUTES.RFQS, icon: FileSpreadsheet, badge: '8 Active' },
  { label: 'Suppliers', path: ROUTES.SUPPLIERS, icon: Users },
  { label: 'Quotations', path: ROUTES.QUOTATIONS, icon: FileCheck2, badge: '14 Pending', badgeVariant: 'warning' },
  { label: 'Comparisons', path: ROUTES.COMPARISON, icon: GitCompare, badge: '3 Ready', badgeVariant: 'success' },
  { label: 'Reports', path: ROUTES.REPORTS, icon: BarChart3 },
  { label: 'Settings', path: ROUTES.SETTINGS, icon: Settings },
];

interface SidebarProps {
  onNavigate?: () => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ onNavigate, className = '' }) => {
  return (
    <aside className={`w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 ${className}`}>
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-200">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-slate-900 rounded-lg text-white shadow-xs">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-base text-slate-900 tracking-tight">QuoteFlow AI</span>
            <span className="block text-[10px] uppercase font-semibold tracking-wider text-slate-400">
              Procurement Suite
            </span>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Workspace Menu
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === ROUTES.DASHBOARD}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-slate-800 text-slate-200'
                          : item.badgeVariant === 'warning'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : item.badgeVariant === 'success'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* AI Extraction Engine Status Card */}
      <div className="p-4 border-t border-slate-200 bg-slate-50/50">
        <div className="rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-2xs">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-800 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>AI Parser Active</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-normal">
            Gemini structured extractor online. OCR document pipeline running.
          </p>
          <div className="mt-2.5 flex items-center justify-between text-[10px] font-medium text-slate-600">
            <span>Accuracy: 99.2%</span>
            <span className="text-emerald-600 font-semibold">Healthy</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
