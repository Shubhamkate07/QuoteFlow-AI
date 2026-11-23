import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Mail, Lock, Building2, User, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { ROUTES } from '../../routes/paths';

export const RegisterPage: React.FC = () => {
  const { register, isLoading, error, clearError } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please fill in all required fields.');
      return;
    }

    if (password.length < 8) {
      setLocalError('Password must contain at least 8 characters.');
      return;
    }

    if (password !== passwordConfirm) {
      setLocalError('Passwords do not match. Please re-enter.');
      return;
    }

    try {
      await register({
        email: email.trim(),
        password,
        password_confirm: passwordConfirm,
        full_name: fullName.trim(),
        organization_name: organizationName.trim(),
      });
      navigate(ROUTES.DASHBOARD, { replace: true });
    } catch (err: any) {
      setLocalError(err?.message || 'Registration failed. Please check form details.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-slate-900 tracking-tight">Create your Account</h3>
        <p className="text-xs text-slate-500 mt-1">
          Set up your procurement team and company workspace
        </p>
      </div>

      {(localError || error) && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start space-x-2.5 text-xs text-rose-800 animate-in fade-in">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{localError || error}</span>
        </div>
      )}

      <form className="space-y-3.5" onSubmit={handleSubmit}>
        <Input
          label="Full Name"
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Sarah Connor"
          leftIcon={<User className="w-4 h-4 text-slate-400" />}
          autoComplete="name"
          required
        />

        <Input
          label="Work Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="buyer@acme-corp.com"
          leftIcon={<Mail className="w-4 h-4 text-slate-400" />}
          autoComplete="email"
          required
        />

        <Input
          label="Company / Workspace Name"
          type="text"
          value={organizationName}
          onChange={(e) => setOrganizationName(e.target.value)}
          placeholder="Acme Aerospace & Manufacturing"
          leftIcon={<Building2 className="w-4 h-4 text-slate-400" />}
          required
        />

        <div className="relative">
          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 8 characters"
            leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
            autoComplete="new-password"
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

        <Input
          label="Confirm Password"
          type={showPassword ? 'text' : 'password'}
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          placeholder="Re-enter password"
          leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
          autoComplete="new-password"
          required
        />

        <Button
          type="submit"
          className="w-full mt-3"
          isLoading={isLoading}
        >
          {isLoading ? 'Creating Account & Workspace...' : 'Create Account & Workspace'}
        </Button>
      </form>

      <div className="pt-2 text-center border-t border-slate-100">
        <p className="text-xs text-slate-500">
          Already have an account?{' '}
          <Link
            to={ROUTES.LOGIN}
            className="font-medium text-slate-900 hover:text-emerald-700 transition-colors underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};
