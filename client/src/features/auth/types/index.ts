/**
 * Authentication and Multi-Tenant User Types
 */

export type OrganizationRole =
  | 'owner'
  | 'admin'
  | 'procurement_manager'
  | 'procurement_user';

export interface UserOrganization {
  id: string;
  name: string;
  slug: string;
  role: OrganizationRole;
  role_display: string;
  is_active: boolean;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  organizations: UserOrganization[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthResponse {
  tokens: AuthTokens;
  user: User;
}

export interface RegisterResponse {
  message: string;
  user: User;
  organization: {
    id: string;
    name: string;
    slug: string;
    role: string;
  };
  tokens: AuthTokens;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  password_confirm: string;
  full_name?: string;
  organization_name?: string;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface AuthContextType {
  user: User | null;
  activeOrganization: UserOrganization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  switchOrganization: (organizationId: string) => void;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}
