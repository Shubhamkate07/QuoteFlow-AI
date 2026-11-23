import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../features/auth/context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { ROUTES } from '../../routes/paths';

export const LoginPage: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || ROUTES.DASHBOARD;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please enter both your work email and password.');
      return;
    }

    try {
      await login({ email: email.trim(), password });
      navigate(from, { replace: true });
    } catch (err: any) {
      setLocalError(err?.message || 'Login failed. Please check your credentials.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-slate-900 tracking-tight">Sign in to QuoteFlow</h3>
        <p className="text-xs text-slate-500 mt-1">
          Access your procurement workspace, quotations, and RFQs
        </p>
      </div>

      {(localError || error) && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start space-x-2.5 text-xs text-rose-800 animate-in fade-in">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{localError || error}</span>
        </div>
      )}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <Input
          label="Work Email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (localError) setLocalError(null);
          }}
          placeholder="buyer@acme-corp.com"
          leftIcon={<Mail className="w-4 h-4 text-slate-400" />}
          autoComplete="email"
          required
        />

        <div className="relative">
          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (localError) setLocalError(null);
            }}
            placeholder="••••••••••••"
            leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-[34px] text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>

        <Button
          type="submit"
          className="w-full mt-2"
          isLoading={isLoading}
        >
          {isLoading ? 'Signing In...' : 'Sign In'}
        </Button>
      </form>

      <div className="pt-2 text-center border-t border-slate-100">
        <p className="text-xs text-slate-500">
          New to QuoteFlow AI?{' '}
          <Link
            to={ROUTES.REGISTER}
            className="font-medium text-slate-900 hover:text-emerald-700 transition-colors underline"
          >
            Create your company workspace
          </Link>
        </p>
      </div>
    </div>
  );
};
