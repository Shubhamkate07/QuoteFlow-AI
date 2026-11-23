import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';
import * as AuthContextModule from '../../features/auth/context/AuthContext';
import { renderWithProviders } from '../../test/test-utils';
import { ROUTES } from '../paths';

vi.mock('../../features/auth/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

describe('ProtectedRoute Route Guard', () => {
  const mockUseAuth = vi.mocked(AuthContextModule.useAuth);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner and message when session is authenticating', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      activeOrganization: null,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      switchOrganization: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
    });

    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Protected Dashboard Content</div>} />
        </Route>
      </Routes>,
      { initialEntries: ['/dashboard'] }
    );

    expect(screen.getByText('Authenticating session...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Dashboard Content')).not.toBeInTheDocument();
  });

  it('redirects unauthenticated user to login with return location state', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      activeOrganization: null,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      switchOrganization: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
    });

    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/rfqs/create" element={<div>Protected RFQ Create</div>} />
        </Route>
        <Route path={ROUTES.LOGIN} element={<div>Login Page Form</div>} />
      </Routes>,
      { initialEntries: ['/rfqs/create'] }
    );

    expect(screen.getByText('Login Page Form')).toBeInTheDocument();
    expect(screen.queryByText('Protected RFQ Create')).not.toBeInTheDocument();
  });

  it('renders protected child routes when user is authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: {
        id: 'usr-1',
        email: 'buyer@acme.com',
        full_name: 'Jane Doe',
        is_staff: false,
        is_active: true,
        date_joined: '2026-01-01',
        organizations: [],
      },
      activeOrganization: {
        id: 'org-1',
        name: 'Acme Corp',
        slug: 'acme-corp',
        role: 'procurement_manager',
        role_display: 'Procurement Manager',
        is_active: true,
        created_at: '2026-01-01',
      },
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      switchOrganization: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
    });

    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Protected Dashboard Content</div>} />
        </Route>
      </Routes>,
      { initialEntries: ['/dashboard'] }
    );

    expect(screen.getByText('Protected Dashboard Content')).toBeInTheDocument();
  });
});
