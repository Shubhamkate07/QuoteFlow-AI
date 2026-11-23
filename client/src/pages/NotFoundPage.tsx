import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FileQuestion, ArrowLeft, Home } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { ROUTES } from '../routes/paths';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
        <div className="inline-flex p-3 bg-emerald-500/10 text-emerald-400 rounded-xl mb-4">
          <FileQuestion className="w-8 h-8" />
        </div>
        <div className="text-4xl font-extrabold text-white tracking-tight mb-2">404</div>
        <h1 className="text-xl font-bold text-white mb-2">Resource Not Found</h1>
        <p className="text-sm text-slate-400 mb-6">
          The requested quotation, RFQ, or procurement page does not exist or has been archived.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate(-1)} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            <span>Go Back</span>
          </Button>
          <Link to={ROUTES.DASHBOARD}>
            <Button size="sm" className="gap-2">
              <Home className="w-4 h-4" />
              <span>Dashboard</span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
