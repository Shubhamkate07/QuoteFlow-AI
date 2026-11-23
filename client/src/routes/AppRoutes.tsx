import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '../layouts/AppLayout';
import { AuthLayout } from '../layouts/AuthLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { RfqListPage } from '../pages/rfq/RfqListPage';
import { RfqDetailPage } from '../pages/rfq/RfqDetailPage';
import { CreateRfqPage } from '../pages/rfq/CreateRfqPage';
import { EditRfqPage } from '../pages/rfq/EditRfqPage';
import { SupplierListPage } from '../pages/suppliers/SupplierListPage';
import { SupplierDetailPage } from '../pages/suppliers/SupplierDetailPage';
import { CreateSupplierPage } from '../pages/suppliers/CreateSupplierPage';
import { EditSupplierPage } from '../pages/suppliers/EditSupplierPage';
import { QuotationsPage } from '../pages/quotations/QuotationsPage';
import { QuotationReviewPage } from '../pages/quotations/QuotationReviewPage';
import { ComparisonPage } from '../pages/comparison/ComparisonPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { ROUTES } from './paths';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public / Authentication Flow (Restricted for already-logged-in users) */}
      <Route element={<PublicRoute />}>
        <Route element={<AuthLayout />}>
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
        </Route>
      </Route>

      {/* Authenticated Workspace Flow (Guarded by ProtectedRoute) */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />

          {/* RFQ Management Routes */}
          <Route path={ROUTES.RFQS} element={<RfqListPage />} />
          <Route path={ROUTES.RFQ_CREATE} element={<CreateRfqPage />} />
          <Route path="/rfqs/:id" element={<RfqDetailPage />} />
          <Route path="/rfqs/:id/edit" element={<EditRfqPage />} />

          {/* Supplier Management Routes */}
          <Route path={ROUTES.SUPPLIERS} element={<SupplierListPage />} />
          <Route path={ROUTES.SUPPLIER_CREATE} element={<CreateSupplierPage />} />
          <Route path="/suppliers/:id" element={<SupplierDetailPage />} />
          <Route path="/suppliers/:id/edit" element={<EditSupplierPage />} />

          {/* Quotations Management Routes */}
          <Route path={ROUTES.QUOTATIONS} element={<QuotationsPage />} />
          <Route path="/quotations/:id/review" element={<QuotationReviewPage />} />

          {/* Supplier Comparison Route */}
          <Route path={ROUTES.COMPARISON} element={<ComparisonPage />} />

          {/* Reports & Audit Deliverables Route */}
          <Route path={ROUTES.REPORTS} element={<ReportsPage />} />
          <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Not Found Fallbacks */}
      <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to={ROUTES.NOT_FOUND} replace />} />
    </Routes>
  );
};
