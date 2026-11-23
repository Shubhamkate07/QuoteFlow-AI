import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../../../components/ui/Card';
import { Button } from '../../../../components/ui/Button';
import { Badge } from '../../../../components/ui/Badge';
import { Input } from '../../../../components/ui/Input';
import { EvidenceBadge } from './EvidenceBadge';
import type { ExtractedLineItemData, FieldEvidence } from '../../types/extraction';
import { formatCurrency } from '../../../../utils/formatters';
import {
  Layers,
  Plus,
  Trash2,
  SlidersHorizontal,
  Tag,
  X,
} from 'lucide-react';

interface ExtractionLineItemsEditorProps {
  items: ExtractedLineItemData[];
  currency: string;
  onChange: (items: ExtractedLineItemData[]) => void;
  onEvidenceClick?: (label: string, evidence: FieldEvidence) => void;
  isReadOnly?: boolean;
}

export const ExtractionLineItemsEditor: React.FC<ExtractionLineItemsEditorProps> = ({
  items = [],
  currency = 'USD',
  onChange,
  onEvidenceClick,
  isReadOnly = false,
}) => {
  const [expandedSpecIndex, setExpandedSpecIndex] = useState<number | null>(null);

  const handleUpdateItem = (index: number, updates: Partial<ExtractedLineItemData>) => {
    const updated = items.map((item, idx) => {
      if (idx !== index) return item;

      const merged = { ...item, ...updates };

      const qty = Number(merged.quantity) || 0;
      const unitPrice = Number(merged.unit_price) || 0;
      const discount = Number(merged.discount) || 0;
      const tax = Number(merged.tax) || 0;

      // Auto-compute total if quantity, unit price, discount or tax changed
      if (
        updates.quantity !== undefined ||
        updates.unit_price !== undefined ||
        updates.discount !== undefined ||
        updates.tax !== undefined
      ) {
        merged.total = Math.round((qty * unitPrice - discount + tax) * 100) / 100;
      }

      return merged;
    });

    onChange(updated);
  };

  const handleDeleteItem = (index: number) => {
    if (isReadOnly) return;
    const updated = items.filter((_, idx) => idx !== index);
    onChange(updated);
  };

  const handleAddItem = () => {
    if (isReadOnly) return;
    const newItem: ExtractedLineItemData = {
      line_number: items.length + 1,
      description: 'New Line Item',
      manufacturer: '',
      model: '',
      quantity: 1,
      unit: 'EA',
      unit_price: 0,
      discount: 0,
      tax: 0,
      total: 0,
      specifications: [],
      confidence_level: 1.0,
    };
    onChange([...items, newItem]);
  };

  const handleAddSpecification = (itemIndex: number) => {
    const item = items[itemIndex];
    const specs = [...(item.specifications || [])];
    specs.push({ name: 'Spec Name', value: 'Value' });
    handleUpdateItem(itemIndex, { specifications: specs });
  };

  const handleUpdateSpecification = (
    itemIndex: number,
    specIndex: number,
    field: 'name' | 'value',
    val: string
  ) => {
    const item = items[itemIndex];
    const specs = (item.specifications || []).map((s, idx) => {
      if (idx !== specIndex) return s;
      return { ...s, [field]: val };
    });
    handleUpdateItem(itemIndex, { specifications: specs });
  };

  const handleDeleteSpecification = (itemIndex: number, specIndex: number) => {
    const item = items[itemIndex];
    const specs = (item.specifications || []).filter((_, idx) => idx !== specIndex);
    handleUpdateItem(itemIndex, { specifications: specs });
  };

  return (
    <Card className="border-slate-200 shadow-2xs">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-slate-900">
                Extracted Line Items & Pricing Schedule
              </CardTitle>
              <p className="text-[11px] text-slate-500">
                Edit quantities, unit prices, discounts, and technical specs
              </p>
            </div>
            <Badge variant="neutral" size="sm">
              {items.length} Item{items.length !== 1 ? 's' : ''}
            </Badge>
          </div>

          {!isReadOnly && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddItem}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Line Item
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {items.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No line items extracted. Click "Add Line Item" to manually enter item rows.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50/90 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-2.5 px-3 w-12 text-center">#</th>
                  <th className="py-2.5 px-3 min-w-[200px]">Description & Model</th>
                  <th className="py-2.5 px-2 text-right w-20">Qty</th>
                  <th className="py-2.5 px-2 text-center w-16">Unit</th>
                  <th className="py-2.5 px-2 text-right w-24">Unit Price</th>
                  <th className="py-2.5 px-2 text-right w-20">Discount</th>
                  <th className="py-2.5 px-2 text-right w-20">Tax</th>
                  <th className="py-2.5 px-3 text-right w-28">Total ({currency})</th>
                  <th className="py-2.5 px-2 text-center w-20">Evidence</th>
                  <th className="py-2.5 px-2 text-center w-16">Specs</th>
                  {!isReadOnly && <th className="py-2.5 px-2 text-center w-10"></th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item, idx) => {
                  const hasSpecs = item.specifications && item.specifications.length > 0;
                  const isSpecExpanded = expandedSpecIndex === idx;

                  const lineEvidence: FieldEvidence = {
                    extracted_value: item.total,
                    source_text: item.source_text,
                    page_number: item.page_number,
                    confidence_level: item.confidence_level,
                  };

                  return (
                    <React.Fragment key={`line-item-${idx}`}>
                      <tr className="hover:bg-slate-50/60 transition-colors">
                        {/* Line number */}
                        <td className="py-2 px-3 text-center font-mono text-slate-400 font-semibold text-[11px]">
                          {item.line_number || idx + 1}
                        </td>

                        {/* Description, Manufacturer & Model */}
                        <td className="py-2 px-3 space-y-1">
                          <Input
                            value={item.description || ''}
                            onChange={(e) => handleUpdateItem(idx, { description: e.target.value })}
                            placeholder="Part / service description..."
                            disabled={isReadOnly}
                            className="text-xs py-1"
                          />
                          <div className="flex items-center gap-1.5 text-[11px]">
                            <Input
                              value={item.manufacturer || ''}
                              onChange={(e) => handleUpdateItem(idx, { manufacturer: e.target.value })}
                              placeholder="Manufacturer (optional)"
                              disabled={isReadOnly}
                              className="text-[11px] py-0.5 text-slate-500"
                            />
                            <Input
                              value={item.model || ''}
                              onChange={(e) => handleUpdateItem(idx, { model: e.target.value })}
                              placeholder="Model / MPN"
                              disabled={isReadOnly}
                              className="text-[11px] py-0.5 text-slate-500"
                            />
                          </div>
                        </td>

                        {/* Quantity */}
                        <td className="py-2 px-2 text-right">
                          <Input
                            type="number"
                            step="any"
                            value={item.quantity || ''}
                            onChange={(e) =>
                              handleUpdateItem(idx, {
                                quantity: e.target.value === '' ? 0 : Number(e.target.value),
                              })
                            }
                            disabled={isReadOnly}
                            className="text-xs py-1 text-right font-mono"
                          />
                        </td>

                        {/* Unit */}
                        <td className="py-2 px-2 text-center">
                          <Input
                            value={item.unit || ''}
                            onChange={(e) => handleUpdateItem(idx, { unit: e.target.value })}
                            placeholder="EA"
                            disabled={isReadOnly}
                            className="text-xs py-1 text-center font-mono uppercase"
                          />
                        </td>

                        {/* Unit Price */}
                        <td className="py-2 px-2 text-right">
                          <Input
                            type="number"
                            step="any"
                            value={item.unit_price || ''}
                            onChange={(e) =>
                              handleUpdateItem(idx, {
                                unit_price: e.target.value === '' ? 0 : Number(e.target.value),
                              })
                            }
                            disabled={isReadOnly}
                            className="text-xs py-1 text-right font-mono font-medium"
                          />
                        </td>

                        {/* Discount */}
                        <td className="py-2 px-2 text-right">
                          <Input
                            type="number"
                            step="any"
                            value={item.discount || ''}
                            onChange={(e) =>
                              handleUpdateItem(idx, {
                                discount: e.target.value === '' ? 0 : Number(e.target.value),
                              })
                            }
                            placeholder="0"
                            disabled={isReadOnly}
                            className="text-xs py-1 text-right font-mono text-slate-500"
                          />
                        </td>

                        {/* Tax */}
                        <td className="py-2 px-2 text-right">
                          <Input
                            type="number"
                            step="any"
                            value={item.tax || ''}
                            onChange={(e) =>
                              handleUpdateItem(idx, {
                                tax: e.target.value === '' ? 0 : Number(e.target.value),
                              })
                            }
                            placeholder="0"
                            disabled={isReadOnly}
                            className="text-xs py-1 text-right font-mono text-slate-500"
                          />
                        </td>

                        {/* Total */}
                        <td className="py-2 px-3 text-right">
                          <span className="font-mono font-bold text-slate-900 text-xs">
                            {formatCurrency(item.total, currency)}
                          </span>
                        </td>

                        {/* Evidence Citation */}
                        <td className="py-2 px-2 text-center">
                          <div
                            onClick={() =>
                              onEvidenceClick?.(`Line Item #${idx + 1}`, lineEvidence)
                            }
                          >
                            <EvidenceBadge evidence={lineEvidence} />
                          </div>
                        </td>

                        {/* Specifications Toggle */}
                        <td className="py-2 px-2 text-center">
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedSpecIndex(isSpecExpanded ? null : idx)
                            }
                            className={`p-1 rounded text-[11px] font-medium transition-colors ${
                              hasSpecs
                                ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                                : 'text-slate-400 hover:text-slate-600'
                            }`}
                            title="Manage technical specifications"
                          >
                            <SlidersHorizontal className="w-3.5 h-3.5" />
                          </button>
                        </td>

                        {/* Delete row */}
                        {!isReadOnly && (
                          <td className="py-2 px-2 text-center">
                            <button
                              type="button"
                              onClick={() => handleDeleteItem(idx)}
                              className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                              title="Delete row"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        )}
                      </tr>

                      {/* Expandable Specifications Sub-panel */}
                      {isSpecExpanded && (
                        <tr className="bg-slate-50/80">
                          <td colSpan={isReadOnly ? 10 : 11} className="p-3">
                            <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-xs text-slate-800 flex items-center gap-1.5">
                                  <Tag className="w-3 h-3 text-indigo-500" />
                                  Technical Specifications for Item #{idx + 1}
                                </span>
                                {!isReadOnly && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleAddSpecification(idx)}
                                    className="text-[11px] py-0.5 h-7"
                                  >
                                    Add Spec
                                  </Button>
                                )}
                              </div>

                              {(!item.specifications || item.specifications.length === 0) ? (
                                <p className="text-[11px] text-slate-400 italic">
                                  No technical specifications listed for this item.
                                </p>
                              ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                                  {item.specifications.map((spec, sIdx) => (
                                    <div
                                      key={`spec-${idx}-${sIdx}`}
                                      className="flex items-center gap-1 bg-slate-50 p-1.5 rounded border border-slate-200 text-xs"
                                    >
                                      <Input
                                        value={spec.name}
                                        onChange={(e) =>
                                          handleUpdateSpecification(
                                            idx,
                                            sIdx,
                                            'name',
                                            e.target.value
                                          )
                                        }
                                        placeholder="Parameter"
                                        disabled={isReadOnly}
                                        className="text-[11px] py-0.5 font-medium"
                                      />
                                      <span className="text-slate-400">:</span>
                                      <Input
                                        value={spec.value}
                                        onChange={(e) =>
                                          handleUpdateSpecification(
                                            idx,
                                            sIdx,
                                            'value',
                                            e.target.value
                                          )
                                        }
                                        placeholder="Value"
                                        disabled={isReadOnly}
                                        className="text-[11px] py-0.5"
                                      />
                                      {!isReadOnly && (
                                        <button
                                          type="button"
                                          onClick={() =>
                                            handleDeleteSpecification(idx, sIdx)
                                          }
                                          className="text-slate-400 hover:text-rose-500 p-0.5"
                                        >
                                          <X className="w-3 h-3" />
                                        </button>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
