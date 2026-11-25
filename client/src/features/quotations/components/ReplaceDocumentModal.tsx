import React, { useState, useRef } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { useQuotation } from '../context/QuotationContext';
import { getErrorMessage } from '../../../lib/api';
import type { Quotation } from '../types';
import {
  RefreshCw,
  UploadCloud,
  FileText,
  FileSpreadsheet,
  FileImage,
  X,
  AlertTriangle,
} from 'lucide-react';

interface ReplaceDocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  quotation: Quotation | null;
}

export const ReplaceDocumentModal: React.FC<ReplaceDocumentModalProps> = ({
  isOpen,
  onClose,
  quotation,
}) => {
  const { replaceDocument } = useQuotation();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!quotation) return null;

  const allowedExtensions = ['pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg'];
  const maxSizeBytes = 25 * 1024 * 1024;

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = file.name.split('.').pop()?.toLowerCase() || '';

    if (!allowedExtensions.includes(ext)) {
      setError(`Unsupported file format (.${ext}). Allowed: PDF, Excel (.xlsx, .xls), or Images (.png, .jpg).`);
      return;
    }

    if (file.size > maxSizeBytes) {
      setError(`File size exceeds 25 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      return;
    }

    setSelectedFile(file);
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

  const handleSubmit = async () => {
    if (!selectedFile) {
      setError('Please select a new document to replace the current quotation.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setUploadProgress(0);

      await replaceDocument(quotation.id, selectedFile, (percent) => {
        setUploadProgress(percent);
      });

      handleClose();
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Failed to upload replacement document. Please try again.');
      setError(message);
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (isSubmitting) return; // Prevent closing during active upload
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    setIsSubmitting(false);
    onClose();
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
      return <FileSpreadsheet className="w-5 h-5 text-emerald-600" />;
    }
    if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') {
      return <FileImage className="w-5 h-5 text-amber-600" />;
    }
    return <FileText className="w-5 h-5 text-rose-600" />;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Replace Quotation Document"
      description={`Attach a replacement document for ${quotation.supplierName} (${quotation.quoteReference}).`}
      maxWidth="md"
      footer={
        <div className="flex items-center justify-end gap-3 w-full">
          <Button variant="outline" type="button" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            type="button"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            disabled={!selectedFile || isSubmitting}
            leftIcon={<RefreshCw className={`w-4 h-4 ${isSubmitting ? 'animate-spin' : ''}`} />}
          >
            {isSubmitting
              ? uploadProgress < 100
                ? `Uploading (${uploadProgress}%)...`
                : 'Finalizing...'
              : 'Replace Document'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Notice */}
        <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-lg flex items-start gap-2.5 text-xs text-indigo-900">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-indigo-600" />
          <div>
            <p className="font-semibold">Document versioning</p>
            <p className="mt-0.5 text-indigo-700">
              The newly uploaded file will become the primary active document for quotation{' '}
              <strong className="font-mono">{quotation.quoteReference}</strong> and securely saved on the server.
            </p>
          </div>
        </div>

        {/* Current Document Summary */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Current Active Document
          </span>
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-800 truncate">
            {getFileIcon(quotation.fileName)}
            <span className="truncate">{quotation.fileName}</span>
            <span className="text-slate-400">({quotation.fileSize})</span>
          </div>
        </div>

        {/* Dropzone for new file */}
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">
            Select Replacement File
          </label>

          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                validateAndSetFile(e.target.files[0]);
              }
            }}
            accept=".pdf,.xlsx,.xls,.csv,.png,.jpg,.jpeg"
            className="hidden"
            disabled={isSubmitting}
          />

          {!selectedFile ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => !isSubmitting && fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01]'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/70 bg-white'
              }`}
            >
              <div className="mx-auto w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mb-2">
                <UploadCloud className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-slate-800">
                Click or drop new quotation document
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                PDF, Excel (.xlsx, .xls), or Scans (up to 25 MB)
              </p>
            </div>
          ) : (
            <div className="border border-slate-200 rounded-xl p-3 bg-emerald-50/40 border-emerald-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5 truncate">
                  <div className="p-1.5 bg-white rounded border border-emerald-200 shrink-0">
                    {getFileIcon(selectedFile.name)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-900 truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-[10px] text-emerald-700 font-medium">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to replace
                    </p>
                  </div>
                </div>
                {!isSubmitting && (
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="p-1 text-slate-400 hover:text-rose-600 hover:bg-white rounded transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Progress bar */}
              {isSubmitting && (
                <div className="mt-3 space-y-1">
                  <div className="flex justify-between text-[11px] text-slate-600 font-medium">
                    <span>Uploading replacement...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full transition-all duration-300 rounded-full"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="mt-2.5 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {error}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
