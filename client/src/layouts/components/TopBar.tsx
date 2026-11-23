import React from 'react';
import { Menu, Search, Bell } from 'lucide-react';
import { WorkspaceSelector } from './WorkspaceSelector';
import { UserProfileMenu } from './UserProfileMenu';

interface TopBarProps {
  onOpenMobileNav: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onOpenMobileNav }) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 lg:px-8 sticky top-0 z-20 shadow-2xs">
      {/* Left: Mobile Toggle & Workspace Switcher */}
      <div className="flex items-center space-x-3">
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="md:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300"
          aria-label="Open mobile navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <WorkspaceSelector />
      </div>

      {/* Center: Global Search Bar */}
      <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Search RFQs, suppliers, quotation items... (Ctrl+K)"
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-slate-800 focus:ring-2 focus:ring-slate-900/10 transition-colors"
          />
        </div>
      </div>

      {/* Right: Actions & User Menu */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* AI Processing Status Pill */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>AI Engine Ready</span>
        </div>

        {/* Notifications */}
        <button
          type="button"
          className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-600 rounded-full" />
        </button>

        <div className="h-5 w-px bg-slate-200 mx-1 hidden sm:block" />

        {/* User Profile Dropdown */}
        <UserProfileMenu />
      </div>
    </header>
  );
};
