import React, { useState, useEffect } from 'react';
import { quotationService } from '../../services/quotationService';
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  ZoomIn,
  ZoomOut,
  ExternalLink,
  Download,
  AlertCircle,
  Loader2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  X,
  RefreshCw,
} from 'lucide-react';

interface DocumentViewerProps {
  documentId?: string;
  fileName?: string;
  fileType?: string;
  activePage?: number;
  evidenceSnippet?: {
    page?: number;
    text?: string;
    fieldName?: string;
  } | null;
  onClearSnippet?: () => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  fileName = 'Quotation Document',
  fileType = 'pdf',
  activePage,
  evidenceSnippet,
  onClearSnippet,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [zoomScale, setZoomScale] = useState<number>(100);
  const [currentPage, setCurrentPage] = useState<number>(activePage || 1);
  const [retryCount, setRetryCount] = useState<number>(0);

  // Sync active page when evidence citation requests it
  useEffect(() => {
    if (activePage && activePage > 0) {
      setCurrentPage(activePage);
    }
  }, [activePage]);

  // Fetch document blob inline
  useEffect(() => {
    let active = true;
    let createdUrl: string | null = null;

    if (!documentId) {
      setBlobUrl(null);
      return;
    }

    setIsLoading(true);
    setLoadError(null);

    quotationService
      .downloadDocumentBlob(documentId, true)
      .then(({ blob }) => {
        if (!active) return;
        createdUrl = URL.createObjectURL(blob);
        setBlobUrl(createdUrl);
        setIsLoading(false);
      })
      .catch(async (err) => {
        if (!active) return;
        console.error('Failed to load document blob for preview:', err);
        let errorDetail = err?.message || 'Unable to load original document preview.';
        if (err?.response?.data instanceof Blob) {
          try {
            const errorText = await err.response.data.text();
            const parsed = JSON.parse(errorText);
            errorDetail = parsed.detail || parsed.message || errorDetail;
          } catch {
            // keep errorDetail
          }
        } else if (err?.response?.data?.detail) {
          errorDetail = err.response.data.detail;
        }
        setLoadError(errorDetail);
        setIsLoading(false);
      });

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [documentId, retryCount]);

  const handleZoomIn = () => setZoomScale((prev) => Math.min(prev + 20, 200));
  const handleZoomOut = () => setZoomScale((prev) => Math.max(prev - 20, 60));
  const handleResetZoom = () => setZoomScale(100);

  const normalizedType = fileType.toLowerCase();
  const isPdf = normalizedType.includes('pdf') || fileName.toLowerCase().endsWith('.pdf');
  const isImage =
    normalizedType.includes('image') ||
    normalizedType.includes('png') ||
    normalizedType.includes('jpg') ||
    normalizedType.includes('jpeg') ||
    fileName.toLowerCase().match(/\.(png|jpg|jpeg|webp)$/i);
  const isExcel =
    normalizedType.includes('excel') ||
    normalizedType.includes('sheet') ||
    fileName.toLowerCase().match(/\.(xlsx|xls|csv)$/i);

  const getFormatIcon = () => {
    if (isExcel) return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
    if (isImage) return <FileImage className="w-4 h-4 text-amber-400" />;
    return <FileText className="w-4 h-4 text-rose-400" />;
  };

  const handleDownload = () => {
    if (blobUrl) {
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  const handleOpenNewTab = () => {
    if (blobUrl) {
      window.open(blobUrl, '_blank');
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-2xl border border-slate-700/80 overflow-hidden shadow-lg select-none">
      {/* Document Toolbar */}
      <div className="bg-slate-850 px-3.5 py-2.5 border-b border-slate-700/80 flex flex-wrap items-center justify-between gap-2 text-slate-200">
        {/* Left: Document details */}
        <div className="flex items-center space-x-2 min-w-0">
          <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 shrink-0">
            {getFormatIcon()}
          </div>
          <div className="min-w-0">
            <span
              className="block text-xs font-semibold text-slate-100 truncate max-w-[200px]"
              title={fileName}
            >
              {fileName}
            </span>
            <span className="block text-[10px] text-slate-400 font-mono">
              Original Supplier File • {isPdf ? 'PDF' : isImage ? 'IMAGE' : isExcel ? 'EXCEL' : 'FILE'}
            </span>
          </div>
        </div>

        {/* Center: Page Controls for multi-page */}
        {isPdf && (
          <div className="flex items-center space-x-1.5 bg-slate-800/90 px-2 py-0.5 rounded-lg border border-slate-700 text-xs">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              className="p-1 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] text-slate-300 px-1">
              Page {currentPage}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => p + 1)}
              className="p-1 hover:text-white transition-colors"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Right: Zoom & Action buttons */}
        <div className="flex items-center space-x-1.5">
          <div className="flex items-center space-x-1 bg-slate-800 px-1.5 py-0.5 rounded-lg border border-slate-700 text-slate-300">
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
              title="Reset Zoom"
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

          {blobUrl && (
            <>
              <button
                type="button"
                onClick={handleOpenNewTab}
                className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-750 transition-colors"
                title="Open document in new window"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleDownload}
                className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-750 transition-colors"
                title="Download original file"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Evidence Snippet Callout Notification Bar */}
      {evidenceSnippet && (
        <div className="bg-indigo-950/90 border-b border-indigo-800 px-3.5 py-2 text-xs text-indigo-100 flex items-start justify-between gap-2 animate-in fade-in">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-indigo-200">
                  Target Field: {evidenceSnippet.fieldName || 'Selected Field'}
                </span>
                {evidenceSnippet.page && (
                  <span className="px-1.5 py-0.2 rounded bg-indigo-800 text-[10px] font-mono font-bold">
                    Page {evidenceSnippet.page}
                  </span>
                )}
              </div>
              {evidenceSnippet.text && (
                <p className="text-[11px] text-indigo-300 font-mono mt-0.5 break-words">
                  "{evidenceSnippet.text}"
                </p>
              )}
            </div>
          </div>
          {onClearSnippet && (
            <button
              type="button"
              onClick={onClearSnippet}
              className="p-1 text-indigo-400 hover:text-white transition-colors"
              title="Dismiss snippet citation"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Main Document Viewer Canvas */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-slate-950/80 relative min-h-[450px]">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center space-y-3 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            <span className="text-xs font-medium">Fetching original quotation file...</span>
          </div>
        ) : loadError ? (
          <div className="max-w-md p-6 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-3">
            <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-200">Document Preview Unavailable</h4>
            <p className="text-xs text-slate-400 leading-relaxed">{loadError}</p>
            {documentId && (
              <div className="flex items-center justify-center gap-2 pt-1 flex-wrap">
                <button
                  type="button"
                  onClick={() => setRetryCount((prev) => prev + 1)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retry Loading
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const { blob, filename } = await quotationService.downloadDocumentBlob(documentId, false);
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = fileName || filename;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      window.URL.revokeObjectURL(url);
                    } catch (e) {
                      console.error('Failed to download document:', e);
                    }
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  Direct Download File
                </button>
              </div>
            )}
          </div>
        ) : !blobUrl ? (
          <div className="max-w-md p-6 bg-slate-900/60 border border-slate-800 rounded-xl text-center space-y-2 text-slate-400">
            <FileText className="w-8 h-8 text-slate-500 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-300">No Document File Attached</h4>
            <p className="text-xs text-slate-500">
              This quotation extraction was executed directly from raw text or external upload.
            </p>
          </div>
        ) : isPdf ? (
          <div
            style={{
              transform: `scale(${zoomScale / 100})`,
              transformOrigin: 'top center',
              width: '100%',
              height: '100%',
            }}
            className="w-full h-full min-h-[600px] transition-transform duration-150"
          >
            <object
              data={`${blobUrl}#page=${currentPage}&toolbar=0&navpanes=0`}
              type="application/pdf"
              className="w-full h-full min-h-[650px] rounded-lg border border-slate-700 bg-white"
            >
              <iframe
                src={`${blobUrl}#page=${currentPage}`}
                title="Quotation Document PDF"
                className="w-full h-full min-h-[650px] rounded-lg border border-slate-700 bg-white"
              />
            </object>
          </div>
        ) : isImage ? (
          <div
            style={{
              transform: `scale(${zoomScale / 100})`,
              transformOrigin: 'top center',
            }}
            className="flex items-center justify-center p-2 transition-transform duration-150"
          >
            <img
              src={blobUrl}
              alt={fileName}
              className="max-w-full rounded-lg shadow-2xl border border-slate-700 object-contain"
            />
          </div>
        ) : isExcel ? (
          <div className="max-w-md p-6 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-3">
            <FileSpreadsheet className="w-10 h-10 text-emerald-500 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-200">Spreadsheet Document</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Excel and CSV spreadsheets cannot be rendered inline in standard canvas.
              You can download the spreadsheet to inspect formulas or view extracted tabular rows on the right.
            </p>
            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download Spreadsheet ({fileName})
            </button>
          </div>
        ) : (
          <div
            style={{
              transform: `scale(${zoomScale / 100})`,
              transformOrigin: 'top center',
            }}
            className="w-full h-full p-4"
          >
            <iframe
              src={blobUrl}
              title={fileName}
              className="w-full h-full min-h-[600px] rounded-lg border border-slate-700 bg-white"
            />
          </div>
        )}
      </div>
    </div>
  );
};
