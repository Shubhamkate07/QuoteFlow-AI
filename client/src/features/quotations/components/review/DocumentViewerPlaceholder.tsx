import React, { useState } from 'react';
import type { Quotation } from '../../types';
import { formatCurrency } from '../../../../utils/formatters';
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Crosshair,
} from 'lucide-react';

interface DocumentViewerPlaceholderProps {
  quotation: Quotation;
  highlightedField?: string | null;
}

export const DocumentViewerPlaceholder: React.FC<DocumentViewerPlaceholderProps> = ({
  quotation,
  highlightedField,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoomScale, setZoomScale] = useState<number>(100);
  const [showBoundingBoxes, setShowBoundingBoxes] = useState<boolean>(true);

  const totalPages = quotation.fileType === 'excel' ? 1 : 2;

  const handleZoomIn = () => setZoomScale((prev) => Math.min(prev + 15, 150));
  const handleZoomOut = () => setZoomScale((prev) => Math.max(prev - 15, 75));
  const handleResetZoom = () => setZoomScale(100);

  const getFormatIcon = () => {
    if (quotation.fileType === 'excel') return <FileSpreadsheet className="w-4 h-4 text-emerald-600" />;
    if (quotation.fileType === 'image') return <FileImage className="w-4 h-4 text-amber-600" />;
    return <FileText className="w-4 h-4 text-rose-600" />;
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/90 rounded-2xl border border-slate-700/80 overflow-hidden shadow-lg select-none">
      {/* Top Document Toolbar */}
      <div className="bg-slate-850 px-4 py-2.5 border-b border-slate-700 flex flex-wrap items-center justify-between gap-3 text-slate-200">
        {/* Left: Document Info */}
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 shrink-0">
            {getFormatIcon()}
          </div>
          <div className="min-w-0">
            <span className="block text-xs font-semibold text-slate-100 truncate max-w-[200px]" title={quotation.fileName}>
              {quotation.fileName}
            </span>
            <span className="block text-[10px] text-slate-400 font-mono">
              {quotation.fileSize} • {quotation.fileType.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Center: Page Controls */}
        <div className="flex items-center space-x-2 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700 text-xs">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            className="p-1 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous Page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-[11px] text-slate-300">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            className="p-1 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next Page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Zoom & Bounding Box Overlays */}
        <div className="flex items-center space-x-1.5">
          <button
            type="button"
            onClick={() => setShowBoundingBoxes(!showBoundingBoxes)}
            className={`px-2 py-1 rounded-md text-[11px] font-medium border flex items-center space-x-1.5 transition-colors ${
              showBoundingBoxes
                ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle AI Extracted Bounding Box Overlays"
          >
            <Crosshair className="w-3 h-3 text-indigo-400" />
            <span className="hidden sm:inline">AI Bounding Boxes</span>
          </button>

          <div className="flex items-center space-x-1 bg-slate-800 px-1.5 py-1 rounded-lg border border-slate-700 text-slate-300">
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1 hover:text-white transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span
              onClick={handleResetZoom}
              className="text-[10px] font-mono w-9 text-center cursor-pointer hover:text-white"
            >
              {zoomScale}%
            </span>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1 hover:text-white transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Viewport Container */}
      <div className="flex-1 overflow-auto p-4 sm:p-6 flex items-start justify-center bg-slate-950/70">
        {/* Document Sheet Simulation */}
        <div
          style={{ transform: `scale(${zoomScale / 100})`, transformOrigin: 'top center' }}
          className="w-full max-w-2xl bg-white text-slate-900 rounded-lg shadow-2xl p-8 sm:p-10 font-sans border border-slate-300 relative transition-transform duration-200 ease-out"
        >
          {/* Header Bounding Box Overlay */}
          <div className="relative group">
            {showBoundingBoxes && (
              <div
                className={`absolute -inset-1.5 rounded border border-dashed pointer-events-none transition-all ${
                  highlightedField === 'supplier'
                    ? 'border-indigo-600 bg-indigo-500/10 ring-2 ring-indigo-400'
                    : 'border-emerald-500/60 bg-emerald-500/5 group-hover:border-emerald-600'
                }`}
              >
                <span className="absolute -top-2.5 right-2 px-1.5 py-0.5 rounded bg-emerald-600 text-[9px] font-mono text-white font-semibold">
                  Supplier OCR (99%)
                </span>
              </div>
            )}

            {/* Simulated Supplier Corporate Letterhead */}
            <div className="flex items-start justify-between border-b-2 border-slate-800 pb-5">
              <div>
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded bg-slate-900 text-white font-bold flex items-center justify-center text-sm tracking-wider">
                    {quotation.supplierName.charAt(0)}
                  </div>
                  <h2 className="text-lg font-extrabold uppercase tracking-tight text-slate-900">
                    {quotation.supplierName}
                  </h2>
                </div>
                <p className="text-[11px] text-slate-600 mt-1 max-w-xs">
                  {quotation.supplierInfo?.address || '100 Industrial Center, Precision Machining Blvd'}
                </p>
                <p className="text-[10px] text-slate-500">
                  Tel: {quotation.supplierInfo?.phone || '+1 (555) 234-5678'} • Email: {quotation.supplierInfo?.email || 'sales@supplier.com'}
                </p>
              </div>

              <div className="text-right">
                <span className="text-xl font-black text-slate-900 tracking-wider block">
                  COMMERCIAL QUOTATION
                </span>
                <span className="text-xs font-mono font-bold text-slate-700 block mt-0.5">
                  Ref: {quotation.quoteReference}
                </span>
                <span className="text-[11px] text-slate-500 block">
                  Date: {quotation.quoteDate || '2026-11-19'}
                </span>
              </div>
            </div>
          </div>

          {/* Recipient & RFQ Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 py-4 border-b border-slate-200 text-xs">
            <div className="space-y-1">
              <span className="font-bold uppercase tracking-wider text-[10px] text-slate-400">
                Quoted To:
              </span>
              <p className="font-semibold text-slate-900">Apex Manufacturing Global Corp.</p>
              <p className="text-slate-600 text-[11px]">Attn: Global Procurement Team</p>
              <p className="text-slate-500 text-[10px]">RFQ Reference: {quotation.rfqNumber}</p>
            </div>

            <div className="relative group space-y-1 text-right">
              {showBoundingBoxes && (
                <div
                  className={`absolute -inset-1 rounded border border-dashed pointer-events-none transition-all ${
                    highlightedField === 'terms'
                      ? 'border-indigo-600 bg-indigo-500/10'
                      : 'border-emerald-500/60 bg-emerald-500/5'
                  }`}
                >
                  <span className="absolute -top-2.5 right-2 px-1 py-0.2 rounded bg-emerald-600 text-[8px] font-mono text-white">
                    Terms (97%)
                  </span>
                </div>
              )}
              <span className="font-bold uppercase tracking-wider text-[10px] text-slate-400">
                Terms & Delivery:
              </span>
              <p className="font-medium text-slate-900">
                Payment: <span className="font-semibold">{quotation.commercialTerms.paymentTerms}</span>
              </p>
              <p className="text-slate-700">
                Lead Time: <span className="font-semibold">{quotation.commercialTerms.deliveryLeadWeeks} Weeks ARO</span>
              </p>
              <p className="text-slate-600 text-[11px]">
                Incoterms: {quotation.commercialTerms.incoterms}
              </p>
            </div>
          </div>

          {/* Line Items Pricing Table with Visual Overlays */}
          <div className="py-5">
            <span className="font-bold uppercase tracking-wider text-[10px] text-slate-500 block mb-2">
              Itemized Quotation Schedule:
            </span>

            <div className="relative group border border-slate-300 rounded overflow-hidden">
              {showBoundingBoxes && (
                <div
                  className={`absolute -inset-1 rounded border-2 border-dashed pointer-events-none transition-all ${
                    highlightedField === 'items'
                      ? 'border-indigo-600 bg-indigo-500/10'
                      : 'border-emerald-500/50 bg-emerald-500/5'
                  }`}
                >
                  <span className="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded bg-emerald-600 text-[9px] font-mono text-white">
                    Table Segment (98% Conf)
                  </span>
                </div>
              )}

              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-100 border-b border-slate-300 text-slate-700 font-bold uppercase text-[10px]">
                  <tr>
                    <th className="py-2 px-3">Item / Description</th>
                    <th className="py-2 px-2 text-right">Qty</th>
                    <th className="py-2 px-2 text-right">UOM</th>
                    <th className="py-2 px-3 text-right">Unit Price</th>
                    <th className="py-2 px-3 text-right">Ext Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {quotation.extractedItems.map((item) => (
                    <tr
                      key={item.id}
                      className={`relative group ${
                        item.status === 'variance' ? 'bg-amber-50/50' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-900">{item.extractedPartName}</div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {item.materialSpec}
                        </div>
                        {item.status === 'variance' && showBoundingBoxes && (
                          <span className="inline-block mt-1 px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 text-[9px] font-semibold border border-amber-300">
                            ⚠ AI Variance: {item.discrepancyNote || 'Material Deviation'}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-2 text-right font-mono text-slate-700">
                        {item.extractedQuantity}
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-500 text-[11px]">
                        {item.extractedUnit}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-800">
                        {formatCurrency(item.unitPrice, quotation.currency)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                        {formatCurrency(item.totalPrice, quotation.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Subtotal, Tax, and Total Summary Box */}
          <div className="flex justify-end pt-2">
            <div className="w-64 space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Quoted Subtotal:</span>
                <span className="font-mono font-medium">{formatCurrency(quotation.subtotal, quotation.currency)}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Tax / VAT ({quotation.taxRatePercentage || 0}%):</span>
                <span className="font-mono">{formatCurrency(quotation.taxAmount, quotation.currency)}</span>
              </div>
              <div className="flex justify-between text-slate-900 font-bold border-t-2 border-slate-800 pt-1.5 text-sm">
                <span>Total Quoted Amount:</span>
                <span className="font-mono text-base">{formatCurrency(quotation.totalAmount, quotation.currency)}</span>
              </div>
            </div>
          </div>

          {/* Footer Terms & Legal Notes */}
          <div className="border-t border-slate-200 mt-6 pt-4 text-[10px] text-slate-500 space-y-1">
            <p>
              <strong>Warranty:</strong> {quotation.commercialTerms.warrantyTerms || 'Standard 12-Month replacement warranty.'}
            </p>
            <p>
              <strong>Validity:</strong> Prices firm until {quotation.commercialTerms.validUntil || '30 days from date of quotation.'}
            </p>
            <div className="flex items-center justify-between pt-3 text-[9px] text-slate-400">
              <span>Authorized Signature: Marcus Vance (Commercial Director)</span>
              <span>Document Page {currentPage} of {totalPages}</span>
            </div>
          </div>

          {/* Document Watermark */}
          <div className="absolute bottom-2 right-3 pointer-events-none text-[9px] text-slate-300 font-mono tracking-widest uppercase">
            Original Source Ingested • Gemini 2.0 Optical Preview
          </div>
        </div>
      </div>
    </div>
  );
};
