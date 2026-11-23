import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className = '',
  label,
}) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-3',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-2 ${className}`}>
      <div
        className={`${sizeMap[size]} border-slate-700 border-t-emerald-500 rounded-full animate-spin`}
        role="status"
        aria-label={label || 'Loading'}
      />
      {label && <span className="text-xs text-slate-400 font-medium">{label}</span>}
    </div>
  );
};
