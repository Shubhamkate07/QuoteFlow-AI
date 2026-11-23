import React, { forwardRef } from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      leftIcon,
      rightIcon,
      className = '',
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer select-none';

    const variantStyles = {
      primary:
        'bg-slate-900 hover:bg-slate-800 text-white shadow-xs focus:ring-slate-900 active:bg-slate-950',
      secondary:
        'bg-slate-100 hover:bg-slate-200 text-slate-800 shadow-xs focus:ring-slate-300 active:bg-slate-200/80',
      outline:
        'border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-xs focus:ring-slate-400 active:bg-slate-100',
      ghost:
        'text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-slate-300 active:bg-slate-200',
      danger:
        'bg-rose-600 hover:bg-rose-700 text-white shadow-xs focus:ring-rose-500 active:bg-rose-800',
    };

    const sizeStyles = {
      sm: 'text-xs px-2.5 py-1.5 gap-1.5 h-8',
      md: 'text-sm px-3.5 py-2 gap-2 h-9',
      lg: 'text-base px-5 py-2.5 gap-2.5 h-11',
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {isLoading ? (
          <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin shrink-0" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
