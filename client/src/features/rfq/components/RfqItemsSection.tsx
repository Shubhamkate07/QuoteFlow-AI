import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../../components/ui/Table';
import { EmptyState } from '../../../components/feedback/EmptyState';
import { RfqItemModal } from './RfqItemModal';
import { DeleteItemModal } from './DeleteItemModal';
import {
  useAddRfqItem,
  useUpdateRfqItem,
  useDeleteRfqItem,
} from '../hooks/useRfqQueries';
import type { RfqItem } from '../types';
import type { RfqItemFormValues } from '../schemas/rfqSchema';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import {
  Plus,
  Edit2,
  Trash2,
  Layers,
  Building,
  Tag,
  Calendar,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface RfqItemsSectionProps {
  rfqId: string;
  items: RfqItem[];
  currency?: string;
  defaultDeliveryDate?: string;
}

export const RfqItemsSection: React.FC<RfqItemsSectionProps> = ({
  rfqId,
  items,
  currency = 'USD',
  defaultDeliveryDate,
}) => {
  const addItemMutation = useAddRfqItem();
  const updateItemMutation = useUpdateRfqItem();
  const deleteItemMutation = useDeleteRfqItem();

  const isSubmitting = addItemMutation.isPending || updateItemMutation.isPending;
  const isDeleting = deleteItemMutation.isPending;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<RfqItem | null>(null);
  const [itemToDelete, setItemToDelete] = useState<RfqItem | null>(null);
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);

  const totalEstimatedBudget = items.reduce((sum, item) => {
    return sum + (item.quantity || 0) * (item.targetUnitPrice || 0);
  }, 0);

  const handleOpenAdd = () => {
    setEditingItem(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (item: RfqItem) => {
    setEditingItem(item);
    setIsModalOpen(true);
  };

  const handleSubmitItem = async (values: RfqItemFormValues) => {
    try {
      if (editingItem) {
        await updateItemMutation.mutateAsync({
          rfqId,
          itemId: editingItem.id,
          values,
        });
      } else {
        await addItemMutation.mutateAsync({
          rfqId,
          values,
        });
      }
      setIsModalOpen(false);
      setEditingItem(null);
    } catch (err) {
      console.error('Failed to save line item:', err);
    }
  };

  const handleConfirmDelete = async () => {
    if (itemToDelete) {
      try {
        await deleteItemMutation.mutateAsync({
          rfqId,
          itemId: itemToDelete.id,
        });
        setItemToDelete(null);
      } catch (err) {
        console.error('Failed to delete line item:', err);
      }
    }
  };

  const toggleExpand = (itemId: string) => {
    setExpandedItemId((prev) => (prev === itemId ? null : itemId));
  };

  return (
    <Card className="shadow-xs">
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <CardTitle>Required Line Items & Specifications</CardTitle>
              <Badge variant="neutral" size="sm" className="font-semibold text-[11px]">
                {items.length} {items.length === 1 ? 'item' : 'items'}
              </Badge>
            </div>
            <CardDescription>
              Detailed Bill of Materials (BOM) items against which supplier bids and landed costs are evaluated
            </CardDescription>
          </div>

          <div className="flex items-center gap-3">
            {totalEstimatedBudget > 0 && (
              <div className="text-right hidden sm:block">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block">
                  Est. Target Budget
                </span>
                <span className="text-sm font-bold text-slate-900">
                  {formatCurrency(totalEstimatedBudget, currency)}
                </span>
              </div>
            )}
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={handleOpenAdd}
            >
              Add Item
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {items.length === 0 ? (
          <EmptyState
            icon={Layers}
            title="No required items added to this RFQ"
            description="Define your parts, quantities, tolerances, and manufacturer preferences to start collecting quotes."
            actionLabel="Add First Item"
            onAction={handleOpenAdd}
            className="m-6"
          />
        ) : (
          <div className="divide-y divide-slate-100">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Item #</TableHead>
                  <TableHead>Part Name & Scope</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Target Price</TableHead>
                  <TableHead>Total Target</TableHead>
                  <TableHead>Delivery</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => {
                  const isExpanded = expandedItemId === item.id;
                  const itemTotal = (item.quantity || 0) * (item.targetUnitPrice || 0);

                  return (
                    <React.Fragment key={item.id}>
                      <TableRow className="group">
                        <TableCell className="font-mono text-xs font-bold text-slate-900">
                          {item.itemNumber}
                        </TableCell>

                        <TableCell>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="font-semibold text-sm text-slate-900 leading-snug">
                                {item.name}
                              </div>
                              {item.description && (
                                <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                                  {item.description}
                                </p>
                              )}
                              <p className="text-xs text-slate-600 font-mono mt-1 bg-slate-50 px-2 py-1 rounded border border-slate-100 line-clamp-1">
                                {item.requiredSpecifications}
                              </p>
                            </div>

                            <button
                              type="button"
                              onClick={() => toggleExpand(item.id)}
                              className="text-slate-400 hover:text-slate-700 p-1 rounded transition-colors shrink-0"
                              title="Toggle full specifications"
                            >
                              {isExpanded ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </TableCell>

                        <TableCell className="font-semibold text-slate-800 whitespace-nowrap">
                          {(item.quantity ?? 0).toLocaleString()} <span className="text-xs text-slate-500">{item.unit}</span>
                        </TableCell>

                        <TableCell className="text-slate-700 font-medium whitespace-nowrap">
                          {item.targetUnitPrice
                            ? formatCurrency(item.targetUnitPrice, currency)
                            : <span className="text-slate-400 italic text-xs">Open</span>}
                        </TableCell>

                        <TableCell className="font-bold text-slate-900 whitespace-nowrap">
                          {itemTotal > 0
                            ? formatCurrency(itemTotal, currency)
                            : <span className="text-slate-400 italic text-xs">-</span>}
                        </TableCell>

                        <TableCell className="text-xs text-slate-600 whitespace-nowrap">
                          {item.requiredDeliveryDate ? (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-slate-400" />
                              {formatDate(item.requiredDeliveryDate)}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">RFQ default</span>
                          )}
                        </TableCell>

                        <TableCell className="text-right whitespace-nowrap">
                          <div className="flex items-center justify-end space-x-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenEdit(item)}
                              className="p-1.5 h-8 w-8 text-slate-500 hover:text-slate-900"
                              title="Edit item"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setItemToDelete(item)}
                              className="p-1.5 h-8 w-8 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                              title="Delete item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>

                      {/* Expandable Specifications & Preferences Details */}
                      {isExpanded && (
                        <tr className="bg-slate-50/80">
                          <td colSpan={7} className="px-6 py-4 border-b border-slate-100">
                            <div className="space-y-3">
                              {/* Full Specifications */}
                              <div>
                                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                                  Full Technical Specifications
                                </span>
                                <p className="text-xs text-slate-800 bg-white p-3 rounded-lg border border-slate-200 leading-relaxed font-mono">
                                  {item.requiredSpecifications}
                                </p>
                              </div>

                              {/* Structured Attributes */}
                              {item.specsList && item.specsList.length > 0 && (
                                <div>
                                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                                    Structured Specification Parameters
                                  </span>
                                  <div className="flex flex-wrap gap-2">
                                    {item.specsList.map((attr, idx) => (
                                      <div
                                        key={idx}
                                        className="inline-flex items-center px-2.5 py-1 rounded-md bg-white border border-slate-200 text-xs shadow-2xs"
                                      >
                                        <span className="font-semibold text-slate-700 mr-1.5">
                                          {attr.key}:
                                        </span>
                                        <span className="text-slate-900 font-mono">
                                          {attr.value}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Preferences and Notes Grid */}
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                                {item.manufacturerPreference && (
                                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs">
                                    <div className="flex items-center space-x-1.5 text-slate-500 mb-1">
                                      <Building className="w-3.5 h-3.5 text-slate-400" />
                                      <span className="font-medium">Manufacturer Preference</span>
                                    </div>
                                    <div className="font-semibold text-slate-800">
                                      {item.manufacturerPreference}
                                    </div>
                                  </div>
                                )}

                                {item.modelPreference && (
                                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs">
                                    <div className="flex items-center space-x-1.5 text-slate-500 mb-1">
                                      <Tag className="w-3.5 h-3.5 text-slate-400" />
                                      <span className="font-medium">Model / OEM Reference</span>
                                    </div>
                                    <div className="font-semibold text-slate-800 font-mono">
                                      {item.modelPreference}
                                    </div>
                                  </div>
                                )}

                                {item.notes && (
                                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs sm:col-span-1">
                                    <span className="font-medium text-slate-500 block mb-1">
                                      Special Handling / Notes
                                    </span>
                                    <div className="text-slate-700">{item.notes}</div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      {/* Add / Edit Item Modal */}
      <RfqItemModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingItem(null);
        }}
        onSubmit={handleSubmitItem}
        initialItem={editingItem}
        currency={currency}
        defaultDeliveryDate={defaultDeliveryDate}
        isSubmitting={isSubmitting}
      />

      {/* Delete Item Confirmation Modal */}
      <DeleteItemModal
        isOpen={Boolean(itemToDelete)}
        item={itemToDelete}
        onClose={() => setItemToDelete(null)}
        onConfirm={handleConfirmDelete}
        isDeleting={isDeleting}
      />
    </Card>
  );
};
