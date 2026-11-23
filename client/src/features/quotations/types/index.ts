export * from './extraction';

export type QuotationStatus =
  | 'uploaded'
  | 'processing'
  | 'completed'
  | 'needs_review'
  | 'failed'
  | 'received'
  | 'under_review'
  | 'accepted'
  | 'rejected'
  | 'expired'
  | 'draft';

export interface ExtractedLineItem {
  id: string;
  rfqItemId?: string;
  extractedPartName: string;
  extractedQuantity: number;
  extractedUnit: string;
  unitPrice: number;
  totalPrice: number;
  materialSpec: string;
  confidenceScore: number; // 0.0 - 1.0
  status: 'matched' | 'variance' | 'unmatched';
  discrepancyNote?: string;
}

export interface CommercialTerms {
  paymentTerms: string;
  deliveryLeadWeeks: number;
  incoterms: string;
  validUntil: string;
  warrantyTerms: string;
  taxesApplicable?: string;
}

export interface ExtractedSupplierInfo {
  companyName: string;
  contactPerson?: string;
  email?: string;
  phone?: string;
  address?: string;
  gstVatNumber?: string;
  website?: string;
}

export interface QuotationDocument {
  id: string;
  quotationId: string;
  originalFilename: string;
  fileType: 'pdf' | 'excel' | 'image';
  fileTypeDisplay: string;
  fileExtension: string;
  fileSize: number;
  fileSizeDisplay: string;
  mimeType: string;
  checksumSha256: string;
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed';
  processingStatusDisplay: string;
  processingProgress: number;
  processingError?: string;
  downloadUrl: string;
  createdAt: string;
}

export interface BackendQuotationDocument {
  id: string;
  quotation_id: string;
  original_filename: string;
  file_type: 'pdf' | 'excel' | 'image';
  file_type_display: string;
  file_extension: string;
  file_size: number;
  file_size_display: string;
  mime_type: string;
  checksum_sha256: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  processing_status_display: string;
  processing_progress: number;
  processing_error?: string;
  download_url: string;
  uploaded_by_email?: string;
  created_at: string;
  updated_at: string;
}

export interface BackendQuotationItem {
  id: string;
  quotation_id: string;
  rfq_item_id: string | null;
  rfq_item_name: string | null;
  match_type: 'exact' | 'substitute' | 'additional' | 'unmatched';
  match_type_display: string;
  position: number;
  description: string;
  manufacturer: string;
  model: string;
  quantity: string | number;
  unit: string;
  unit_price: string | number;
  discount: string | number;
  tax: string | number;
  line_total: string | number;
  specifications: Record<string, unknown>;
  lead_time_days?: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BackendQuotation {
  id: string;
  quotation_number: string;
  rfq_id: string;
  rfq_number?: string;
  rfq_title?: string;
  supplier_id: string;
  supplier_name?: string;
  status: string;
  status_display?: string;
  currency: string;
  delivery_terms?: string;
  payment_terms?: string;
  warranty_information?: string;
  lead_time_weeks?: string | number | null;
  subtotal: string | number;
  tax_amount: string | number;
  total_amount: string | number;
  quotation_date?: string | null;
  validity_date?: string | null;
  is_expired?: boolean;
  notes?: string;
  document?: string | null;
  documents?: BackendQuotationDocument[];
  items?: BackendQuotationItem[];
  items_count?: number;
  documents_count?: number;
  created_by_email?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface Quotation {
  id: string;
  rfqId: string;
  rfqNumber: string;
  supplierId: string;
  supplierName: string;
  supplierInfo?: ExtractedSupplierInfo;
  quoteReference: string;
  quoteDate?: string;
  fileName: string;
  fileSize: string;
  fileType: 'pdf' | 'excel' | 'image';
  uploadedAt: string;
  status: QuotationStatus;
  processingProgress: number; // 0 - 100
  processingError?: string;
  currency: string;
  taxRatePercentage?: number;
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  commercialTerms: CommercialTerms;
  extractedItems: ExtractedLineItem[];
  documents?: QuotationDocument[];
  reviewNotes?: string;
  overallConfidenceScore?: number; // 0.0 - 1.0
  fieldConfidence?: Record<string, number>;
  missingFields?: string[];
  isApproved?: boolean;
  approvedAt?: string;
  approvedBy?: string;
}

export interface UploadQuotationPayload {
  rfqId: string;
  supplierId: string;
  supplierName?: string;
  file: File;
  quoteReference?: string;
  currency?: string;
}

export function adaptBackendDocument(backend: BackendQuotationDocument): QuotationDocument {
  return {
    id: backend.id,
    quotationId: backend.quotation_id,
    originalFilename: backend.original_filename,
    fileType: backend.file_type,
    fileTypeDisplay: backend.file_type_display,
    fileExtension: backend.file_extension,
    fileSize: backend.file_size,
    fileSizeDisplay: backend.file_size_display,
    mimeType: backend.mime_type,
    checksumSha256: backend.checksum_sha256,
    processingStatus: backend.processing_status,
    processingStatusDisplay: backend.processing_status_display,
    processingProgress: backend.processing_progress || 0,
    processingError: backend.processing_error,
    downloadUrl: backend.download_url,
    createdAt: backend.created_at,
  };
}

export function adaptBackendQuotation(backend: BackendQuotation): Quotation {
  const docs = (backend.documents || []).map(adaptBackendDocument);
  const primaryDoc = docs[0];

  let fileType: 'pdf' | 'excel' | 'image' = 'pdf';
  if (primaryDoc) {
    fileType = primaryDoc.fileType;
  } else if (backend.document) {
    const ext = backend.document.split('.').pop()?.toLowerCase();
    if (ext === 'xlsx' || ext === 'xls') fileType = 'excel';
    else if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') fileType = 'image';
  }

  const subtotal = Number(backend.subtotal) || 0;
  const taxAmount = Number(backend.tax_amount) || 0;
  const totalAmount = Number(backend.total_amount) || 0;

  // Map backend status to frontend display status
  let mappedStatus: QuotationStatus = 'completed';
  if (backend.status === 'received' || backend.status === 'draft') {
    mappedStatus = 'uploaded';
  } else if (backend.status === 'under_review') {
    mappedStatus = 'needs_review';
  } else if (backend.status === 'accepted') {
    mappedStatus = 'completed';
  } else if (backend.status === 'rejected' || backend.status === 'expired') {
    mappedStatus = 'completed';
  }

  const extractedItems: ExtractedLineItem[] = (backend.items || []).map((item) => ({
    id: item.id,
    rfqItemId: item.rfq_item_id || undefined,
    extractedPartName: item.description,
    extractedQuantity: Number(item.quantity) || 0,
    extractedUnit: item.unit,
    unitPrice: Number(item.unit_price) || 0,
    totalPrice: Number(item.line_total) || 0,
    materialSpec: item.manufacturer ? `${item.manufacturer} ${item.model}`.trim() : '',
    confidenceScore: 1.0,
    status: item.match_type === 'substitute' ? 'variance' : 'matched',
    discrepancyNote: item.match_type === 'substitute' ? 'Alternative specification proposed' : undefined,
  }));

  return {
    id: backend.id,
    rfqId: backend.rfq_id,
    rfqNumber: backend.rfq_number || 'RFQ',
    supplierId: backend.supplier_id,
    supplierName: backend.supplier_name || 'Vendor',
    quoteReference: backend.quotation_number,
    quoteDate: backend.quotation_date || undefined,
    fileName: primaryDoc?.originalFilename || (backend.document ? backend.document.split('/').pop() || 'document.pdf' : 'document.pdf'),
    fileSize: primaryDoc?.fileSizeDisplay || '25.0 KB',
    fileType: fileType,
    uploadedAt: backend.created_at,
    status: mappedStatus,
    processingProgress: primaryDoc?.processingProgress || 100,
    processingError: primaryDoc?.processingError,
    currency: backend.currency || 'USD',
    subtotal: subtotal,
    taxAmount: taxAmount,
    totalAmount: totalAmount,
    documents: docs,
    commercialTerms: {
      paymentTerms: backend.payment_terms || 'Standard',
      deliveryLeadWeeks: Number(backend.lead_time_weeks) || 0,
      incoterms: backend.delivery_terms || 'FOB',
      validUntil: backend.validity_date || '',
      warrantyTerms: backend.warranty_information || 'Standard Manufacturer Warranty',
    },
    extractedItems: extractedItems,
  };
}
