import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import {
  Sliders,
  DollarSign,
  Layers,
  Clock,
  CreditCard,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import {
  type ScoringWeightsConfig,
  DEFAULT_WEIGHTS,
  WEIGHT_PRESETS,
} from '../types';

interface CustomWeightsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentWeights?: ScoringWeightsConfig;
  onSaveWeights: (weights: ScoringWeightsConfig, regenerate: boolean) => Promise<void> | void;
  isSaving?: boolean;
}

export const CustomWeightsModal: React.FC<CustomWeightsModalProps> = ({
  isOpen,
  onClose,
  currentWeights = DEFAULT_WEIGHTS,
  onSaveWeights,
  isSaving = false,
}) => {
  const [weights, setWeights] = useState<ScoringWeightsConfig>({ ...currentWeights });
  const [regenerate, setRegenerate] = useState(true);

  // Sync when currentWeights changes
  useEffect(() => {
    if (isOpen) {
      setWeights({ ...currentWeights });
    }
  }, [isOpen, currentWeights]);

  const totalSum =
    Number(weights.price || 0) +
    Number(weights.spec_match || 0) +
    Number(weights.delivery || 0) +
    Number(weights.payment_terms || 0) +
    Number(weights.warranty || 0);

  const isValidSum = totalSum === 100;
  const difference = 100 - totalSum;

  const handleWeightChange = (key: keyof ScoringWeightsConfig, val: number) => {
    const num = Math.max(0, Math.min(100, isNaN(val) ? 0 : val));
    setWeights((prev) => ({
      ...prev,
      [key]: num,
    }));
  };

  const handleApplyPreset = (presetWeights: ScoringWeightsConfig) => {
    setWeights({ ...presetWeights });
  };

  const handleResetDefault = () => {
    setWeights({ ...DEFAULT_WEIGHTS });
  };

  const handleSave = async () => {
    if (!isValidSum) return;
    await onSaveWeights(weights, regenerate);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Customize Supplier Scoring Weights"
      description="Configure objective evaluation weights to align supplier ranking with your organization's procurement priorities."
      maxWidth="2xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetDefault}
            leftIcon={<RotateCcw className="w-3.5 h-3.5 text-slate-500" />}
            disabled={isSaving}
          >
            Reset Default
          </Button>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose} disabled={isSaving}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={!isValidSum || isSaving}
              isLoading={isSaving}
              leftIcon={<Sliders className="w-3.5 h-3.5" />}
            >
              Apply & Re-Score
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Sum Status Banner */}
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between transition-colors ${
            isValidSum
              ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
              : 'bg-amber-50/90 border-amber-300 text-amber-900'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            {isValidSum ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
            )}
            <div>
              <div className="text-xs font-bold">
                {isValidSum
                  ? 'Weights Valid: Exactly 100% Allocated'
                  : `Weights Incomplete: Total is ${totalSum}% (${difference > 0 ? `+${difference}% remaining` : `${Math.abs(difference)}% over target`})`}
              </div>
              <p className="text-[11px] opacity-80 mt-0.5">
                Deterministic mathematical scoring requires all 5 factors to sum strictly to 100%.
              </p>
            </div>
          </div>

          <div className="text-right">
            <span
              className={`font-mono text-2xl font-black ${
                isValidSum ? 'text-emerald-700' : 'text-amber-700'
              }`}
            >
              {totalSum}%
            </span>
          </div>
        </div>

        {/* Quick Presets */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Select Procurement Weighting Preset:</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {WEIGHT_PRESETS.map((preset) => {
              const isActive =
                weights.price === preset.weights.price &&
                weights.spec_match === preset.weights.spec_match &&
                weights.delivery === preset.weights.delivery &&
                weights.payment_terms === preset.weights.payment_terms &&
                weights.warranty === preset.weights.warranty;

              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleApplyPreset(preset.weights)}
                  className={`p-2.5 text-left rounded-lg border text-xs transition-all ${
                    isActive
                      ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-semibold shadow-2xs'
                      : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                  }`}
                >
                  <div className="font-semibold text-xs text-slate-900">{preset.name}</div>
                  <div className="text-[10px] text-slate-500 font-mono mt-1">
                    {preset.weights.price}% / {preset.weights.spec_match}% / {preset.weights.delivery}%
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Sliders / Inputs for the 5 Factors */}
        <div className="space-y-3.5 pt-1">
          {/* Factor 1: Price */}
          <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-emerald-50 text-emerald-600 border border-emerald-200">
                  <DollarSign className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900">Price Competitiveness</span>
                  <span className="text-[10px] text-slate-400 block">
                    Scaled relative to lowest competitive quoted bid
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={weights.price}
                  onChange={(e) => handleWeightChange('price', Number(e.target.value))}
                  className="w-16 px-2 py-1 text-right text-xs font-mono font-bold border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-xs font-mono font-semibold text-slate-600">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={weights.price}
              onChange={(e) => handleWeightChange('price', Number(e.target.value))}
              className="w-full accent-emerald-600 h-1.5 bg-slate-100 rounded-lg cursor-pointer"
            />
          </div>

          {/* Factor 2: Specification Match */}
          <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-indigo-50 text-indigo-600 border border-indigo-200">
                  <Layers className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900">Specification Match</span>
                  <span className="text-[10px] text-slate-400 block">
                    Technical parameter compliance and deviation penalty
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={weights.spec_match}
                  onChange={(e) => handleWeightChange('spec_match', Number(e.target.value))}
                  className="w-16 px-2 py-1 text-right text-xs font-mono font-bold border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-xs font-mono font-semibold text-slate-600">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={weights.spec_match}
              onChange={(e) => handleWeightChange('spec_match', Number(e.target.value))}
              className="w-full accent-indigo-600 h-1.5 bg-slate-100 rounded-lg cursor-pointer"
            />
          </div>

          {/* Factor 3: Delivery Schedule */}
          <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-sky-50 text-sky-600 border border-sky-200">
                  <Clock className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900">Delivery Lead Time</span>
                  <span className="text-[10px] text-slate-400 block">
                    On-time schedule fulfillment against RFQ required date
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={weights.delivery}
                  onChange={(e) => handleWeightChange('delivery', Number(e.target.value))}
                  className="w-16 px-2 py-1 text-right text-xs font-mono font-bold border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-xs font-mono font-semibold text-slate-600">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={weights.delivery}
              onChange={(e) => handleWeightChange('delivery', Number(e.target.value))}
              className="w-full accent-sky-600 h-1.5 bg-slate-100 rounded-lg cursor-pointer"
            />
          </div>

          {/* Factor 4: Payment Terms */}
          <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-purple-50 text-purple-600 border border-purple-200">
                  <CreditCard className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900">Commercial Payment Terms</span>
                  <span className="text-[10px] text-slate-400 block">
                    Working capital liquidity and advance payment penalty
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={weights.payment_terms}
                  onChange={(e) => handleWeightChange('payment_terms', Number(e.target.value))}
                  className="w-16 px-2 py-1 text-right text-xs font-mono font-bold border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-xs font-mono font-semibold text-slate-600">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={weights.payment_terms}
              onChange={(e) => handleWeightChange('payment_terms', Number(e.target.value))}
              className="w-full accent-purple-600 h-1.5 bg-slate-100 rounded-lg cursor-pointer"
            />
          </div>

          {/* Factor 5: Warranty Coverage */}
          <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-teal-50 text-teal-600 border border-teal-200">
                  <ShieldCheck className="w-3.5 h-3.5" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900">Warranty Coverage</span>
                  <span className="text-[10px] text-slate-400 block">
                    Duration and post-delivery defect liability guarantee
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={weights.warranty}
                  onChange={(e) => handleWeightChange('warranty', Number(e.target.value))}
                  className="w-16 px-2 py-1 text-right text-xs font-mono font-bold border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-xs font-mono font-semibold text-slate-600">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={weights.warranty}
              onChange={(e) => handleWeightChange('warranty', Number(e.target.value))}
              className="w-full accent-teal-600 h-1.5 bg-slate-100 rounded-lg cursor-pointer"
            />
          </div>
        </div>

        {/* Immediate Recalculate Option */}
        <label className="flex items-center gap-2.5 p-3 bg-slate-50 border border-slate-200 rounded-xl cursor-pointer text-xs">
          <input
            type="checkbox"
            checked={regenerate}
            onChange={(e) => setRegenerate(e.target.checked)}
            className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
          />
          <span className="font-medium text-slate-700">
            Regenerate comparison rankings and persist snapshot immediately upon saving
          </span>
        </label>
      </div>
    </Modal>
  );
};
