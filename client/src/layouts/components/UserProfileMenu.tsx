import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User as UserIcon, Settings, ShieldCheck, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../../features/auth/context/AuthContext';
import { ROUTES } from '../../routes/paths';

export const UserProfileMenu: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user, activeOrganization, logout } = useAuth();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    setIsOpen(false);
    await logout();
    navigate(ROUTES.LOGIN);
  };

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'Procurement User';
  const displayEmail = user?.email || 'user@company.com';
  const roleDisplay = activeOrganization?.role_display || 'Member';

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.email.slice(0, 2).toUpperCase() || 'QF';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-3 p-1.5 rounded-lg hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300 cursor-pointer"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-semibold shadow-xs">
          {initials}
        </div>
        <div className="hidden lg:block text-left pr-1">
          <div className="text-xs font-semibold text-slate-800 leading-tight">{displayName}</div>
          <div className="text-[11px] text-slate-500 leading-tight">{roleDisplay}</div>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden lg:block" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white border border-slate-200 shadow-xl py-1.5 z-50">
          {/* User Details */}
          <div className="px-4 py-3 border-b border-slate-100">
            <div className="text-xs font-semibold text-slate-900">{displayName}</div>
            <div className="text-xs text-slate-500 truncate">{displayEmail}</div>
            <div className="mt-1.5 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              {roleDisplay}
            </div>
          </div>

          {/* Links */}
          <div className="py-1">
            <Link
              to={ROUTES.SETTINGS}
              onClick={() => setIsOpen(false)}
              className="flex items-center space-x-2.5 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
            >
              <UserIcon className="w-4 h-4 text-slate-400" />
              <span>Profile & Account</span>
            </Link>

            <Link
              to={ROUTES.SETTINGS}
              onClick={() => setIsOpen(false)}
              className="flex items-center space-x-2.5 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
            >
              <Settings className="w-4 h-4 text-slate-400" />
              <span>Workspace Settings</span>
            </Link>

            <div className="flex items-center space-x-2.5 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors">
              <ShieldCheck className="w-4 h-4 text-slate-400" />
              <span>Audit Log & Approvals</span>
            </div>
          </div>

          {/* Sign Out */}
          <div className="border-t border-slate-100 pt-1">
            <button
              type="button"
              onClick={handleSignOut}
              className="w-full flex items-center space-x-2.5 px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors text-left cursor-pointer"
            >
              <LogOut className="w-4 h-4 text-rose-500" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
