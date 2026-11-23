import React, { type ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../lib/queryClient';
import { ErrorBoundary } from '../components/feedback/ErrorBoundary';
import { AuthProvider } from '../features/auth/context/AuthContext';
import { RfqProvider } from '../features/rfq/context/RfqContext';
import { SupplierProvider } from '../features/suppliers/context/SupplierContext';
import { QuotationProvider } from '../features/quotations/context/QuotationContext';

interface AppProvidersProps {
  children: ReactNode;
}

/**
 * Top-level application providers wrapping Routing, Query Client, Error Boundary, Auth, and Domain Providers
 */
export const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <SupplierProvider>
              <RfqProvider>
                <QuotationProvider>
                  {children}
                </QuotationProvider>
              </RfqProvider>
            </SupplierProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
