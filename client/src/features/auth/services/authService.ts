import api, { tokenStorage } from '../../../lib/api';
import type {
  LoginCredentials,
  RegisterPayload,
  AuthResponse,
  RegisterResponse,
  User,
  ChangePasswordPayload,
} from '../types';

export const authService = {
  /**
   * Authenticates user with email and password
   */
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/login/', credentials);
    const { tokens, user } = response.data;
    tokenStorage.setTokens(tokens.access, tokens.refresh);
    if (user.organizations && user.organizations.length > 0) {
      tokenStorage.setActiveOrgId(user.organizations[0].id);
    }
    return response.data;
  },

  /**
   * Registers a new user and sets up their initial company workspace
   */
  register: async (payload: RegisterPayload): Promise<RegisterResponse> => {
    const response = await api.post<RegisterResponse>('/auth/register/', payload);
    const { tokens, organization } = response.data;
    tokenStorage.setTokens(tokens.access, tokens.refresh);
    if (organization?.id) {
      tokenStorage.setActiveOrgId(organization.id);
    }
    return response.data;
  },

  /**
   * Fetches the current authenticated user's profile and memberships
   */
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me/');
    return response.data;
  },

  /**
   * Updates user's personal details (e.g. full_name)
   */
  updateProfile: async (data: { full_name: string }): Promise<User> => {
    const response = await api.patch<User>('/auth/me/', data);
    return response.data;
  },

  /**
   * Changes account password
   */
  changePassword: async (data: ChangePasswordPayload): Promise<void> => {
    await api.post('/auth/change-password/', data);
  },

  /**
   * Logs out user and revokes refresh token on the server
   */
  logout: async (): Promise<void> => {
    const refresh = tokenStorage.getRefreshToken();
    try {
      if (refresh) {
        await api.post('/auth/logout/', { refresh });
      }
    } finally {
      tokenStorage.clearTokens();
    }
  },
};
