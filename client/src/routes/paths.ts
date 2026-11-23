/**
 * Centralized Route Paths for QuoteFlow AI
 */
export const ROUTES = {
  ROOT: '/',
  DASHBOARD: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  RFQS: '/rfqs',
  RFQ_CREATE: '/rfqs/new',
  RFQ_DETAIL: (id: string = ':id') => `/rfqs/${id}`,
  RFQ_EDIT: (id: string = ':id') => `/rfqs/${id}/edit`,
  SUPPLIERS: '/suppliers',
  SUPPLIER_CREATE: '/suppliers/new',
  SUPPLIER_DETAIL: (id: string = ':id') => `/suppliers/${id}`,
  SUPPLIER_EDIT: (id: string = ':id') => `/suppliers/${id}/edit`,
  QUOTATIONS: '/quotations',
  QUOTATION_REVIEW: (id: string = ':id') => `/quotations/${id}/review`,
  COMPARISON: '/comparison',
  REPORTS: '/reports',
  SETTINGS: '/settings',
  NOT_FOUND: '/404',
} as const;
