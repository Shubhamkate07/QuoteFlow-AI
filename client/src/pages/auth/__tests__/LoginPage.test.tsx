import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginPage } from '../LoginPage';
import * as AuthContextModule from '../../../features/auth/context/AuthContext';
import { renderWithProviders } from '../../../test/test-utils';

vi.mock('../../../features/auth/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: { from: { pathname: '/rfqs' } } }),
  };
});

describe('LoginPage UI and Form Validation', () => {
  const mockLogin = vi.fn();
  const mockClearError = vi.fn();
  const mockUseAuth = vi.mocked(AuthContextModule.useAuth);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: null,
      clearError: mockClearError,
      isAuthenticated: false,
      user: null,
      activeOrganization: null,
      register: vi.fn(),
      logout: vi.fn(),
      switchOrganization: vi.fn(),
      refreshUser: vi.fn(),
    });
  });

  it('renders sign in heading, input fields, and submit button', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByText('Sign in to QuoteFlow')).toBeInTheDocument();
    expect(screen.getByLabelText(/work email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument();
  });

  it('validates empty inputs and blocks form submission', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    const submitBtn = screen.getByRole('button', { name: /^sign in$/i });
    await user.click(submitBtn);

    expect(mockLogin).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('toggles password visibility when eye button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    const passwordInput = screen.getByPlaceholderText('••••••••••••');
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleBtn = screen.getByLabelText(/show password/i);
    await user.click(toggleBtn);

    expect(passwordInput).toHaveAttribute('type', 'text');
  });

  it('successfully submits credentials and navigates to target path', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValueOnce({
      user: { id: '1', email: 'test@acme.com' },
      tokens: { access: 'acc', refresh: 'ref' },
    });

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/work email/i), 'buyer@acme.com');
    await user.type(screen.getByPlaceholderText('••••••••••••'), 'SecurePass123!');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    expect(mockLogin).toHaveBeenCalledWith({
      email: 'buyer@acme.com',
      password: 'SecurePass123!',
    });
    expect(mockNavigate).toHaveBeenCalledWith('/rfqs', { replace: true });
  });

  it('displays error alert when login API fails', async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValueOnce(new Error('Invalid email or password credentials.'));

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/work email/i), 'wrong@acme.com');
    await user.type(screen.getByPlaceholderText('••••••••••••'), 'WrongPass');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    expect(
      await screen.findByText('Invalid email or password credentials.')
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('shows loading state on button during submission', () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isLoading: true,
      error: null,
      clearError: mockClearError,
      isAuthenticated: false,
      user: null,
      activeOrganization: null,
      register: vi.fn(),
      logout: vi.fn(),
      switchOrganization: vi.fn(),
      refreshUser: vi.fn(),
    });

    renderWithProviders(<LoginPage />);

    const submitBtn = screen.getByRole('button', { name: /signing in\.\.\./i });
    expect(submitBtn).toBeDisabled();
  });
});
