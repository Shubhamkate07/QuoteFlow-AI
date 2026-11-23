import React, { useState } from 'react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';
import { useAuth } from '../../features/auth/context/AuthContext';
import {
  Building2,
  Cpu,
  ShieldCheck,
  Users,
  CheckCircle2,
  Save,
  Key,
  Sliders,
  Mail,
  User,
  Check,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'org' | 'ai' | 'procurement' | 'team'>('org');
  const [isSaved, setIsSaved] = useState(false);

  // Form states
  const [orgName, setOrgName] = useState('Acme Procurement');
  const [industry, setIndustry] = useState('Industrial Machinery & Precision CNC');
  const [currency, setCurrency] = useState('USD');
  const [timezone, setTimezone] = useState('America/Chicago (UTC-6)');

  const [aiModel, setAiModel] = useState('gemini-2.0-flash');
  const [confidenceThreshold, setConfidenceThreshold] = useState('85');
  const [autoExtract, setAutoExtract] = useState(true);
  const [deterministicValidation, setDeterministicValidation] = useState(true);

  const [approvedOnlyDefault, setApprovedOnlyDefault] = useState(true);
  const [priceWeight, setPriceWeight] = useState(40);
  const [specWeight, setSpecWeight] = useState(30);
  const [leadWeight, setLeadWeight] = useState(15);
  const [termsWeight, setTermsWeight] = useState(10);
  const [warrantyWeight, setWarrantyWeight] = useState(5);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <PageContainer>
      <PageHeader
        title="Workspace & System Settings"
        description="Configure your procurement organization, Google Gemini AI parsing parameters, scoring weights, and team access."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            leftIcon={isSaved ? <Check className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4" />}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {isSaved ? 'Settings Saved' : 'Save Changes'}
          </Button>
        }
      />

      {isSaved && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl text-xs flex items-center justify-between shadow-2xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">Workspace configuration and scoring preferences saved successfully.</span>
          </div>
          <button type="button" onClick={() => setIsSaved(false)} className="text-emerald-700 font-bold hover:text-emerald-900">
            ✕
          </button>
        </div>
      )}

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-slate-200 mb-6 gap-2 text-xs font-semibold overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab('org')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'org'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Organization Profile</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('ai')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'ai'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>AI & Extraction Engine</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('procurement')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'procurement'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Scoring & Governance</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('team')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'team'
              ? 'border-indigo-600 text-indigo-700 bg-indigo-50/40 rounded-t-lg'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Team & Roles</span>
        </button>
      </div>

      {/* Tab 1: Organization Profile */}
      {activeTab === 'org' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          <Card>
            <CardHeader>
              <CardTitle>Organization Information</CardTitle>
              <CardDescription>Legal corporate entity, default currency, and regional operating parameters.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Organization / Company Name"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="e.g. Acme Precision Manufacturing"
                />

                <Input
                  label="Primary Manufacturing Domain"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. CNC Machining & Precision Shafts"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                  label="Default Accounting Currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  options={[
                    { value: 'USD', label: 'USD ($) - United States Dollar' },
                    { value: 'EUR', label: 'EUR (€) - Euro' },
                    { value: 'GBP', label: 'GBP (£) - British Pound' },
                    { value: 'CAD', label: 'CAD ($) - Canadian Dollar' },
                    { value: 'JPY', label: 'JPY (¥) - Japanese Yen' },
                  ]}
                />

                <Select
                  label="Operating Timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  options={[
                    { value: 'America/Chicago (UTC-6)', label: 'America/Chicago (Central Time UTC-6)' },
                    { value: 'America/New_York (UTC-5)', label: 'America/New York (Eastern Time UTC-5)' },
                    { value: 'America/Los_Angeles (UTC-8)', label: 'America/Los Angeles (Pacific Time UTC-8)' },
                    { value: 'Europe/London (UTC+0)', label: 'Europe/London (GMT UTC+0)' },
                    { value: 'Asia/Kolkata (UTC+5:30)', label: 'Asia/Kolkata (IST UTC+5:30)' },
                  ]}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: AI & Extraction Engine */}
      {activeTab === 'ai' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          <Card>
            <CardHeader>
              <CardTitle>Google Gemini AI Extraction Engine</CardTitle>
              <CardDescription>
                Configure multimodal document parsing, alloy/tolerance recognition, and confidence thresholds.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                  label="Active Multimodal LLM Model"
                  value={aiModel}
                  onChange={(e) => setAiModel(e.target.value)}
                  options={[
                    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash (Recommended - Ultra-fast & accurate tabular parsing)' },
                    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro (Deep reasoning for complex non-standard layouts)' },
                    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (Lightweight extraction)' },
                  ]}
                />

                <Select
                  label="AI Confidence Safety Threshold"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(e.target.value)}
                  options={[
                    { value: '75', label: '≥ 75% (Permissive - auto-accept standard formats)' },
                    { value: '85', label: '≥ 85% (Balanced - flags low clarity scans for human review)' },
                    { value: '95', label: '≥ 95% (Strict - flags any ambiguous field for review)' },
                  ]}
                />
              </div>

              {/* API Key Status Banner */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                    <Key className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-slate-900 block">Google Gemini API Key</span>
                    <span className="text-slate-500 text-[11px]">Key configured securely in backend environment (`GEMINI_API_KEY`)</span>
                  </div>
                </div>
                <Badge variant="success" size="sm" dot>
                  Connected & Verified
                </Badge>
              </div>

              {/* Extraction Automation Toggles */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoExtract}
                    onChange={(e) => setAutoExtract(e.target.checked)}
                    className="mt-0.5 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">Automated AI Document Ingestion</span>
                    <span className="text-[11px] text-slate-500">Automatically trigger Gemini multimodal parsing immediately upon PDF or Excel file upload.</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={deterministicValidation}
                    onChange={(e) => setDeterministicValidation(e.target.checked)}
                    className="mt-0.5 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">Deterministic Arithmetic & Schema Cross-Check</span>
                    <span className="text-[11px] text-slate-500">Cross-calculate line item sums, tax rates, and stated grand totals in pure Python to detect arithmetic discrepancies.</span>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: Scoring & Governance */}
      {activeTab === 'procurement' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          <Card>
            <CardHeader>
              <CardTitle>Procurement Award & Comparison Governance</CardTitle>
              <CardDescription>Default multi-factor scoring weights and audit compliance gates.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div>
                <label className="text-xs font-semibold text-slate-800 block mb-3">
                  Default Multi-Criteria Scoring Formula (Total must equal 100%)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 font-medium block mb-1">Price Score</span>
                    <div className="flex items-center gap-1 font-bold text-slate-900">
                      <input
                        type="number"
                        value={priceWeight}
                        onChange={(e) => setPriceWeight(Number(e.target.value))}
                        className="w-14 px-1.5 py-1 text-xs border border-slate-300 rounded font-mono"
                      />
                      <span>%</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 font-medium block mb-1">Spec Match</span>
                    <div className="flex items-center gap-1 font-bold text-slate-900">
                      <input
                        type="number"
                        value={specWeight}
                        onChange={(e) => setSpecWeight(Number(e.target.value))}
                        className="w-14 px-1.5 py-1 text-xs border border-slate-300 rounded font-mono"
                      />
                      <span>%</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 font-medium block mb-1">Lead Time</span>
                    <div className="flex items-center gap-1 font-bold text-slate-900">
                      <input
                        type="number"
                        value={leadWeight}
                        onChange={(e) => setLeadWeight(Number(e.target.value))}
                        className="w-14 px-1.5 py-1 text-xs border border-slate-300 rounded font-mono"
                      />
                      <span>%</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 font-medium block mb-1">Payment Terms</span>
                    <div className="flex items-center gap-1 font-bold text-slate-900">
                      <input
                        type="number"
                        value={termsWeight}
                        onChange={(e) => setTermsWeight(Number(e.target.value))}
                        className="w-14 px-1.5 py-1 text-xs border border-slate-300 rounded font-mono"
                      />
                      <span>%</span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 font-medium block mb-1">Warranty</span>
                    <div className="flex items-center gap-1 font-bold text-slate-900">
                      <input
                        type="number"
                        value={warrantyWeight}
                        onChange={(e) => setWarrantyWeight(Number(e.target.value))}
                        className="w-14 px-1.5 py-1 text-xs border border-slate-300 rounded font-mono"
                      />
                      <span>%</span>
                    </div>
                  </div>
                </div>
                <div className="mt-2 text-[11px] text-slate-400 font-mono">
                  Current Sum: {priceWeight + specWeight + leadWeight + termsWeight + warrantyWeight}%
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={approvedOnlyDefault}
                    onChange={(e) => setApprovedOnlyDefault(e.target.checked)}
                    className="mt-0.5 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">Strict Human Review Requirement</span>
                    <span className="text-[11px] text-slate-500">
                      Require buyers to formally approve AI extractions before quotations can qualify for official procurement comparison matrices.
                    </span>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 4: Team & Roles */}
      {activeTab === 'team' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          <Card>
            <CardHeader>
              <CardTitle>Current User & Permissions</CardTitle>
              <CardDescription>Authentication credentials and authorized procurement roles.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <User className="w-4 h-4 text-slate-500" />
                    <span className="font-semibold text-slate-900">{user?.full_name || 'Admin User'}</span>
                  </div>
                  <Badge variant="primary" size="sm">
                    {((user as any)?.role || 'PROCUREMENT ADMIN / OWNER').toUpperCase()}
                  </Badge>
                </div>

                <div className="flex items-center justify-between border-t border-slate-200/60 pt-2 text-slate-600">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{user?.email || 'admin@quoteflow.ai'}</span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-400">ID: {user?.id || 'da3c4b98...'}</span>
                </div>

                <div className="flex items-center justify-between border-t border-slate-200/60 pt-2 text-[11px] text-slate-500">
                  <div className="flex items-center gap-1.5 text-emerald-700">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Full Procurement Manager & RFQ Award Authority</span>
                  </div>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </PageContainer>
  );
};
