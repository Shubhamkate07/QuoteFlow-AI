import React, { useState, useRef } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { useSuppliers } from '../../suppliers/context/SupplierContext';
import { useQuotation } from '../context/QuotationContext';
import type { RfqItem } from '../../rfq/types';
import {
  UploadCloud,
  FileText,
  FileSpreadsheet,
  FileImage,
  X,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';

interface QuotationUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  rfqId: string;
  rfqCurrency: string;
  rfqItems: RfqItem[];
  invitedSupplierIds?: string[];
}

export const QuotationUploadModal: React.FC<QuotationUploadModalProps> = ({
  isOpen,
  onClose,
  rfqId,
  rfqCurrency,
  rfqItems,
  invitedSupplierIds = [],
}) => {
  const { suppliers } = useSuppliers();
  const { uploadQuotation } = useQuotation();

  // Filter suppliers: prefer invited suppliers or show all active suppliers
  const eligibleSuppliers = suppliers.filter(
    (s) => invitedSupplierIds.length === 0 || invitedSupplierIds.includes(s.id)
  );
  const displaySuppliers = eligibleSuppliers.length > 0 ? eligibleSuppliers : suppliers;

  const [selectedSupplierId, setSelectedSupplierId] = useState<string>(
    displaySuppliers[0]?.id || ''
  );
  const [quoteReference, setQuoteReference] = useState<string>('');
  const [currency, setCurrency] = useState<string>(rfqCurrency || 'USD');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = ['pdf', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'];
  const maxSizeBytes = 25 * 1024 * 1024; // 25 MB

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = file.name.split('.').pop()?.toLowerCase() || '';

    if (!allowedExtensions.includes(ext)) {
      setError(`Unsupported file format (.${ext}). Please upload a PDF, Excel (.xlsx/.xls), or scanned image (.png/.jpg).`);
      return;
    }

    if (file.size > maxSizeBytes) {
      setError(`File size exceeds 25 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      return;
    }

    setSelectedFile(file);
    if (!quoteReference) {
      const baseName = file.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9-_]/g, '-');
      setQuoteReference(`QT-${baseName.substring(0, 16)}`);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select or drop a quotation document to upload.');
      return;
    }

    const supplierId = selectedSupplierId || displaySuppliers[0]?.id;
    if (!supplierId) {
      setError('Please select the bidding supplier for this quotation.');
      return;
    }

    const supplier = suppliers.find((s) => s.id === supplierId);
    if (!supplier) {
      setError('Selected supplier not found.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setUploadProgress(10);

      await uploadQuotation(
        {
          rfqId,
          supplierId: supplier.id,
          supplierName: supplier.companyName,
          file: selectedFile,
          quoteReference: quoteReference.trim() || undefined,
          currency: currency,
        },
        rfqItems,
        (progress) => {
          setUploadProgress(progress);
        }
      );

      handleClose();
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: Record<string, unknown> } };
      const data = apiErr.response?.data;
      let message = 'Upload failed. Please check your document and try again.';
      if (data) {
        if (typeof data.detail === 'string') {
          message = data.detail;
        } else if (typeof data.message === 'string') {
          message = data.message;
        } else if (typeof data.error === 'string') {
          message = data.error;
        } else {
          // Flatten DRF validation error dict into human-readable field errors
          const errorEntries = Object.entries(data)
            .map(([field, errVal]) => {
              const text = Array.isArray(errVal) ? errVal.join(', ') : String(errVal);
              return `${field.replace(/_/g, ' ')}: ${text}`;
            });
          if (errorEntries.length > 0) {
            message = errorEntries.join(' | ');
          }
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
      setIsSubmitting(false);
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setQuoteReference('');
    setError(null);
    setIsSubmitting(false);
    setUploadProgress(0);
    onClose();
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'xlsx' || ext === 'xls') {
      return <FileSpreadsheet className="w-8 h-8 text-emerald-600" />;
    }
    if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') {
      return <FileImage className="w-8 h-8 text-amber-600" />;
    }
    return <FileText className="w-8 h-8 text-rose-600" />;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Supplier Quotation"
      description="Ingest supplier bids (PDF, Excel, Scan) into QuoteFlow AI for automated quotation management."
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-end gap-3 w-full">
          <Button variant="outline" type="button" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="submit"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            disabled={!selectedFile || isSubmitting}
            leftIcon={<UploadCloud className="w-4 h-4" />}
          >
            {isSubmitting ? `Uploading (${uploadProgress}%)...` : 'Upload Quotation'}
          </Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {/* Supplier Selector */}
        <Select
          label="Bidding Supplier"
          required
          value={selectedSupplierId || displaySuppliers[0]?.id || ''}
          onChange={(e) => setSelectedSupplierId(e.target.value)}
          options={displaySuppliers.map((s) => ({
            value: s.id,
            label: `${s.companyName} (${s.category})`,
          }))}
          helperText="Select which supplier issued this quotation document."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Quote Reference / ID"
            placeholder="e.g. QT-2026-881A"
            value={quoteReference}
            onChange={(e) => setQuoteReference(e.target.value)}
            helperText="Supplier's formal proposal or invoice number."
          />

          <Select
            label="Currency Standard"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            options={[
              { value: 'USD', label: 'USD - US Dollar ($)' },
              { value: 'EUR', label: 'EUR - Euro (€)' },
              { value: 'GBP', label: 'GBP - British Pound (£)' },
              { value: 'CAD', label: 'CAD - Canadian Dollar ($)' },
              { value: 'JPY', label: 'JPY - Japanese Yen (¥)' },
              { value: 'INR', label: 'INR - Indian Rupee (₹)' },
            ]}
          />
        </div>

        {/* Drag-and-drop Dropzone */}
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">
            Quotation Document <span className="text-rose-500">*</span>
          </label>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg"
            className="hidden"
          />

          {!selectedFile ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01]'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/70 bg-white'
              }`}
            >
              <div className="mx-auto w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                Click to browse or drag & drop quotation file
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supports Adobe PDF, Excel (.xlsx, .xls), and Scans (.png, .jpg) up to 25 MB
              </p>
              <div className="flex items-center justify-center gap-2 mt-4 text-[11px] text-slate-400">
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Multi-page tables
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Commercial terms
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Authenticated storage
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 flex items-center justify-between">
                <div className="flex items-center space-x-3 truncate">
                  <div className="p-2 bg-white rounded-lg border border-slate-200 shrink-0">
                    {getFileIcon(selectedFile.name)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-900 truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for secure upload
                    </p>
                  </div>
                </div>
                {!isSubmitting && (
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1 text-slate-400 hover:text-rose-600 hover:bg-white rounded-md transition-colors"
                    title="Remove selected file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Upload Progress Bar */}
              {isSubmitting && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-medium text-slate-600">
                    <span>Uploading document...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </form>
    </Modal>
  );
};
